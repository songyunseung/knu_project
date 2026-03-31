# stomp_manager.py
import asyncio
import stomp
import json
import time
import threading
import logging
from datetime import datetime
from collections import deque

import config

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────
# STOMP 리스너 (재연결 + 수신 메시지 디스패치)
# ─────────────────────────────────────────────────
class _StompListener(stomp.ConnectionListener):

    def __init__(self, controller: "UIController"):
        self._ctrl = controller

    def on_connected(self, frame):
        logger.info("STOMP 서버 연결 성공: %s:%s", config.STOMP_HOST, config.STOMP_PORT)
        self._ctrl._connected = True
        # 연결(재연결) 시 구독 자동 복구
        self._ctrl._subscribe_all()
        self._ctrl._flush_pending_queue()

    def on_disconnected(self):
        logger.warning("STOMP 연결 끊김 — 자동 재연결 시도")
        self._ctrl._connected = False
        self._ctrl._schedule_reconnect()

    def on_error(self, frame):
        logger.error("STOMP 에러 프레임: %s", frame.body)

    def on_message(self, frame):
        """
        프론트로부터 수신한 메시지를 파싱하여 등록된 핸들러로 전달.
        ⚠️ 이 메서드는 STOMP 리스너 스레드에서 실행된다.
           → _dispatch_message 내부에서 call_soon_threadsafe를 통해
             asyncio 루프로 안전하게 위임한다.
        """
        dest = frame.headers.get("destination", "")
        try:
            payload = json.loads(frame.body)
        except json.JSONDecodeError:
            logger.warning("수신 메시지 JSON 파싱 실패: %s", frame.body[:200])
            return

        logger.info("수신 ← [%s] action=%s", dest, payload.get("action"))
        self._ctrl._dispatch_message(dest, payload)


# ─────────────────────────────────────────────────
# UIController
# ─────────────────────────────────────────────────
class UIController:
    """
    STOMP 기반 프론트엔드 양방향 통신 컨트롤러.

    ★ 스레드 안전성 설계:
       stomp.py 라이브러리는 자체 리스너 스레드에서 on_message를 호출한다.
       그런데 main.py의 핸들러들은 asyncio 루프에 의존하는 코드
       (loop.call_later, create_task 등)를 사용한다.

       → 해결: connect() 시 asyncio 루프를 주입받고,
         _dispatch_message에서 call_soon_threadsafe로
         모든 핸들러 실행을 asyncio 루프 스레드에 위임한다.
    """

    def __init__(self):
        self._connected = False
        self._reconnecting = False
        self._pending_queue: deque = deque(maxlen=100)
        self._loop: asyncio.AbstractEventLoop | None = None

        # 이벤트 핸들러 레지스트리: { action_name: callback(payload) }
        self._handlers: dict[str, callable] = {}

        # STOMP 연결 객체 생성만 (실제 연결은 connect()에서)
        self.conn = stomp.Connection(
            [(config.STOMP_HOST, config.STOMP_PORT)],
            heartbeats=(10000, 10000)
        )
        self.conn.set_listener("main", _StompListener(self))

    # ── 연결 / 재연결 ──────────────────────────
    def connect(self, loop: asyncio.AbstractEventLoop):
        """
        STOMP 연결을 시작한다.

        Parameters
        ----------
        loop : asyncio.AbstractEventLoop
            ★ asyncio 이벤트 루프를 주입받아,
              STOMP 스레드에서 핸들러를 안전하게 스케줄링한다.
        """
        self._loop = loop
        self._do_connect()

    def _do_connect(self):
        try:
            self.conn.connect(wait=True)
        except Exception as e:
            logger.error("STOMP 연결 실패: %s", e)
            self._connected = False
            self._schedule_reconnect()

    def _schedule_reconnect(self):
        if self._reconnecting:
            return
        self._reconnecting = True

        def _loop():
            delay = config.STOMP_RECONNECT_DELAY
            for attempt in range(1, config.STOMP_MAX_RECONNECT_TRIES + 1):
                if self._connected:
                    break
                logger.info("STOMP 재연결 시도 %d/%d (%ds 후)",
                            attempt, config.STOMP_MAX_RECONNECT_TRIES, delay)
                time.sleep(delay)
                try:
                    self.conn.connect(wait=True)
                    break
                except Exception as e:
                    logger.warning("  재연결 실패: %s", e)
                    delay = min(delay * 2, 30)
            else:
                logger.critical("STOMP 재연결 최대 시도 초과 — 수동 점검 필요")
            self._reconnecting = False

        threading.Thread(target=_loop, daemon=True).start()

    # ── 구독 ────────────────────────────────────
    def _subscribe_all(self):
        """연결/재연결 시 필요한 토픽을 모두 구독"""
        subs = [
            (config.STOMP_SUB_FRONT_EVENTS, "sub-events"),
            (config.STOMP_SUB_FRONT_ACK,    "sub-ack"),
        ]
        for dest, sub_id in subs:
            try:
                self.conn.subscribe(destination=dest, id=sub_id, ack="auto")
                logger.info("구독 등록: %s", dest)
            except Exception as e:
                logger.error("구독 실패 [%s]: %s", dest, e)

    # ══════════════════════════════════════════════
    #  ★ 핵심 수정: 스레드-안전 메시지 디스패치
    # ══════════════════════════════════════════════
    def register_handler(self, action: str, callback):
        """
        특정 action에 대한 핸들러를 등록한다.
        callback(payload: dict) — 동기 함수 또는 코루틴 함수 모두 지원.
        """
        self._handlers[action] = callback
        logger.info("핸들러 등록: action='%s'", action)

    def _dispatch_message(self, destination: str, payload: dict):
        """
        ★ STOMP 리스너 스레드에서 호출된다.

        동작 방식:
        1. asyncio 루프가 설정되어 있으면
           → call_soon_threadsafe 로 asyncio 루프 스레드에 핸들러 실행을 위임
        2. 코루틴 핸들러는 create_task 로 감싸서 스케줄링
        3. 동기 핸들러도 asyncio 루프 스레드에서 실행
           (loop.call_later 등 루프 의존 코드가 안전하게 동작)
        """
        action = payload.get("action")
        handler = self._handlers.get(action)
        if not handler:
            logger.debug("미등록 action 수신 무시: %s", action)
            return

        # asyncio 루프가 없거나 닫혀 있으면 폴백: 현재 스레드에서 직접 실행
        if self._loop is None or self._loop.is_closed():
            logger.warning(
                "asyncio 루프 미설정 — 현재 스레드에서 핸들러 직접 실행: %s", action
            )
            try:
                handler(payload)
            except Exception as e:
                logger.error("핸들러 오류 [%s]: %s", action, e)
            return

        if asyncio.iscoroutinefunction(handler):
            # ★ 코루틴 핸들러 → asyncio 루프에 태스크로 스케줄링
            def _schedule_coro():
                self._loop.create_task(
                    self._safe_async_handler(action, handler, payload)
                )

            self._loop.call_soon_threadsafe(_schedule_coro)
        else:
            # ★ 동기 핸들러 → asyncio 루프 스레드에서 실행
            def _run_sync():
                try:
                    handler(payload)
                except Exception as e:
                    logger.error("핸들러 오류 [%s]: %s", action, e)

            self._loop.call_soon_threadsafe(_run_sync)

    @staticmethod
    async def _safe_async_handler(action: str, handler, payload: dict):
        """코루틴 핸들러를 예외 안전하게 실행하는 래퍼"""
        try:
            await handler(payload)
        except Exception as e:
            logger.error("비동기 핸들러 오류 [%s]: %s", action, e)

    # ── 대기 큐 플러시 ──────────────────────────
    def _flush_pending_queue(self):
        sent = 0
        while self._pending_queue:
            dest, body = self._pending_queue.popleft()
            try:
                self.conn.send(body=body, destination=dest)
                sent += 1
            except Exception as e:
                self._pending_queue.appendleft((dest, body))
                logger.warning("큐 플러시 중 전송 실패: %s", e)
                break
        if sent:
            logger.info("대기 큐 메시지 %d건 전송 완료", sent)

    # ── 송신 ────────────────────────────────────
    def send_command(self, session_id, action, payload=None) -> bool:
        message = {
            "action": action,
            "timestamp": datetime.now().isoformat(),
            "data": payload or {}
        }
        dest = f"/topic/ui/{session_id}" if session_id else "/topic/ui/global"
        body = json.dumps(message)

        if not self._connected:
            logger.warning("STOMP 미연결 — 대기 큐 보관: %s", action)
            self._pending_queue.append((dest, body))
            return False

        try:
            self.conn.send(body=body, destination=dest)
            return True
        except Exception as e:
            logger.error("메시지 전송 오류: %s — 대기 큐 보관", e)
            self._pending_queue.append((dest, body))
            self._connected = False
            self._schedule_reconnect()
            return False

    # ── 모드 변경 (공식 진입점) ──────────────────
    def adapt_mode(self, user_type) -> bool:
        settings = config.USER_CONFIGS.get(user_type, config.USER_CONFIGS["NORMAL"])
        success = self.send_command(None, "ADAPT_UI", {
            "userType": user_type,
            "settings": settings
        })
        logger.info("UI 모드 송출: %s [%s]", user_type, "성공" if success else "큐 대기")
        return success

    # ── 종료 ────────────────────────────────────
    def disconnect(self):
        try:
            self.conn.disconnect()
        except Exception:
            pass
        self._loop = None
        logger.info("STOMP 연결 종료")