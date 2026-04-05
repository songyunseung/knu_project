# session_manager.py
import asyncio
import time
import logging
from enum import Enum
from dataclasses import dataclass, field

import config

logger = logging.getLogger(__name__)


class SessionState(Enum):
    """세션 생명주기 상태"""
    WAITING   = "WAITING"      # 세션 생성됨, 서비스 진입 대기
    ACTIVE    = "ACTIVE"       # 서비스 이용 중
    COMPLETED = "COMPLETED"    # 정상 종료
    TIMEOUT   = "TIMEOUT"      # 시간 초과로 만료
    ERROR     = "ERROR"        # 오류로 중단


@dataclass
class Session:
    session_id: str
    user_type: str
    service_id: int | None = None
    state: SessionState = SessionState.WAITING
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)

    def touch(self):
        """활동 시각 갱신"""
        self.last_activity = time.time()

    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > config.SESSION_TIMEOUT_SEC

    def is_idle(self) -> bool:
        """세션 내 마지막 활동으로부터 타임아웃 초과 여부"""
        return (time.time() - self.last_activity) > config.SESSION_TIMEOUT_SEC


class SessionManager:
    """활성 세션을 추적하고 만료 세션을 자동 정리한다."""

    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._cleanup_task: asyncio.Task | None = None

    # ── 생명주기 ────────────────────────────────
    def start(self):
        """백그라운드 정리 루프 시작 (이벤트 루프 내에서 호출)"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("세션 매니저 시작 — 정리 주기: %ds", config.SESSION_CLEANUP_INTERVAL)

    async def stop(self):
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
        logger.info("세션 매니저 종료")

    # ── 세션 CRUD ───────────────────────────────
    def create(self, session_id: str, user_type: str) -> Session:
        session = Session(session_id=session_id, user_type=user_type)
        self._sessions[session_id] = session
        logger.info("세션 생성: %s (유형: %s)", session_id, user_type)
        return session

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def activate(self, session_id: str, service_id: int) -> Session | None:
        """세션을 ACTIVE 상태로 전환 + 서비스 ID 기록"""
        session = self._sessions.get(session_id)
        if session and session.state == SessionState.WAITING:
            session.state = SessionState.ACTIVE
            session.service_id = service_id
            session.touch()
            logger.info("세션 활성화: %s → 서비스 %d", session_id, service_id)
        return session

    def touch(self, session_id: str):
        """프론트 이벤트 수신 시 활동 시각 갱신"""
        session = self._sessions.get(session_id)
        if session:
            session.touch()

    def complete(self, session_id: str):
        """서비스 정상 완료"""
        session = self._sessions.get(session_id)
        if session:
            session.state = SessionState.COMPLETED
            logger.info("세션 완료: %s", session_id)

    def fail(self, session_id: str):
        """오류로 세션 중단"""
        session = self._sessions.get(session_id)
        if session:
            session.state = SessionState.ERROR
            logger.warning("세션 오류 중단: %s", session_id)

    def remove(self, session_id: str):
        removed = self._sessions.pop(session_id, None)
        if removed:
            logger.info("세션 제거: %s (상태: %s)", session_id, removed.state.value)

    # ── 조회 ────────────────────────────────────
    @property
    def active_count(self) -> int:
        return sum(1 for s in self._sessions.values()
                   if s.state in (SessionState.WAITING, SessionState.ACTIVE))

    def get_active_session_ids(self) -> list[str]:
        return [sid for sid, s in self._sessions.items()
                if s.state in (SessionState.WAITING, SessionState.ACTIVE)]

    # ── 만료 콜백 (main에서 등록) ────────────────
    # 만료된 세션 처리를 외부에서 주입할 수 있도록 콜백 제공
    _on_timeout_callback = None

    def set_timeout_callback(self, callback):
        """callback(session: Session) — 만료 시 호출할 함수 등록"""
        self._on_timeout_callback = callback

    # ── 백그라운드 정리 ─────────────────────────
    async def _cleanup_loop(self):
        """주기적으로 만료 세션을 정리"""
        while True:
            await asyncio.sleep(config.SESSION_CLEANUP_INTERVAL)
            now = time.time()
            expired_ids = [
                sid for sid, s in self._sessions.items()
                if s.state in (SessionState.WAITING, SessionState.ACTIVE)
                and (now - s.last_activity) > config.SESSION_TIMEOUT_SEC
            ]
            for sid in expired_ids:
                session = self._sessions[sid]
                session.state = SessionState.TIMEOUT
                logger.warning(
                    "세션 타임아웃: %s (서비스: %s, 경과: %.0f초)",
                    sid, session.service_id,
                    now - session.created_at
                )
                if self._on_timeout_callback:
                    try:
                        self._on_timeout_callback(session)
                    except Exception as e:
                        logger.error("타임아웃 콜백 오류: %s", e)

            # 종료 상태(COMPLETED, TIMEOUT, ERROR) 세션 최종 제거
            done_ids = [
                sid for sid, s in self._sessions.items()
                if s.state in (SessionState.COMPLETED, SessionState.TIMEOUT, SessionState.ERROR)
            ]
            for sid in done_ids:
                self._sessions.pop(sid, None)

            if expired_ids or done_ids:
                logger.info(
                    "세션 정리 완료 — 만료: %d, 제거: %d, 잔여 활성: %d",
                    len(expired_ids), len(done_ids), self.active_count
                )