# main.py
import asyncio
import logging

import config
from stomp_manager import UIController
from mcp_client import MCPToolManager, MCPError
from intent_analyzer import IntentAnalyzer
from session_manager import SessionManager, SessionState

# ──────────────────────────────────────────────
# 로깅 설정
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("kiosk.main")


class KioskMainController:

    def __init__(self):
        self.ui = UIController()
        self.mcp = MCPToolManager()
        self.ai = IntentAnalyzer()
        self.sessions = SessionManager()
        self.current_user_type = "NORMAL"

        # 유휴 타이머 핸들
        self._idle_handle: asyncio.TimerHandle | None = None
        self._warning_handle: asyncio.TimerHandle | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

        # ── 프론트 이벤트 핸들러 등록 ────────────
        self.ui.register_handler("USER_TOUCH",       self._on_user_touch)
        self.ui.register_handler("SERVICE_COMPLETE",  self._on_service_complete)
        self.ui.register_handler("UI_ACK",            self._on_ui_ack)
        self.ui.register_handler("USER_CANCEL",       self._on_user_cancel)

        # 세션 타임아웃 콜백
        self.sessions.set_timeout_callback(self._on_session_timeout)

    # ─────────────────────────────────────────────
    # 초기화 / 종료
    # ─────────────────────────────────────────────
    async def start(self):
        """이벤트 루프 내에서 호출 — 비동기 컴포넌트 기동"""
        self._loop = asyncio.get_running_loop()

        # 수정 1: asyncio 루프를 UIController에 주입
        #   → STOMP 리스너 스레드의 콜백이 call_soon_threadsafe로
        #     asyncio 루프에 안전하게 핸들러 실행을 위임한다.
        self.ui.connect(loop=self._loop)

        self.sessions.start()
        self._reset_idle_timer()
        logger.info("키오스크 컨트롤러 기동 완료")

    async def shutdown(self):
        self._cancel_idle_timer()
        await self.sessions.stop()
        await self.mcp.disconnect()
        self.ui.disconnect()
        logger.info("키오스크 컨트롤러 종료 완료")

    # ═════════════════════════════════════════════
    #  외부 트리거 처리
    # ═════════════════════════════════════════════
    async def handle_request(self, trigger_type, data):
        # 어떤 입력이든 유휴 타이머 리셋
        self._reset_idle_timer()

        if trigger_type == "CHANGE_MODE":
            self._change_mode(data)

        elif trigger_type == "VOICE_INPUT":
            await self._handle_voice(data)

        elif trigger_type == "TOUCH_SERVICE":
            await self._handle_touch(data)

        else:
            logger.warning("알 수 없는 trigger_type: %s", trigger_type)

    # ─────────────────────────────────────────────
    # 모드 변경 (단일 진입점)
    # ─────────────────────────────────────────────
    def _change_mode(self, user_type: str):
        if user_type not in config.USER_CONFIGS:
            logger.warning("미지원 사용자 유형 '%s' → NORMAL 대체", user_type)
            user_type = "NORMAL"

        self.current_user_type = user_type
        self.ui.adapt_mode(self.current_user_type)

    # ─────────────────────────────────────────────
    # 음성 입력
    # ─────────────────────────────────────────────
    async def _handle_voice(self, data):
        try:
            ai_res = self.ai.parse_voice_intent(data)
        except Exception as e:
            logger.error("[AI 분석 실패] %s", e)
            return

        if not ai_res or ai_res.get("confidence", 0) < 0.6:
            logger.info("AI 분석 신뢰도 부족 — 요청 무시")
            return

        self._change_mode(ai_res.get("userType", "NORMAL"))

        service_id = ai_res.get("serviceId")
        if service_id is None:
            logger.info("AI 응답에 serviceId 없음 — 서비스 진입 생략")
            return

        await self._execute_service(service_id)

    # ─────────────────────────────────────────────
    # 터치 입력
    # ─────────────────────────────────────────────
    async def _handle_touch(self, service_id):
        if service_id is None:
            logger.warning("service_id 비어 있음 — 요청 무시")
            return
        await self._execute_service(service_id)

    # ─────────────────────────────────────────────
    # 서비스 실행 (MCP 호출 + 세션 관리 + 페이지 이동)
    # ─────────────────────────────────────────────
    async def _execute_service(self, service_id):
        #  수정 2: MCP 응답 검증 — required_fields로 필수 키 보장
        try:
            mcp_result = await self.mcp.call_service(
                "start_session",
                {"userType": self.current_user_type},
                required_fields=["sessionId"],          # ← 필수 필드 명시
            )
        except ConnectionError as e:
            logger.error("[MCP 연결 실패] %s", e)
            return
        except MCPError as e:
            # ★ 응답 형식이 올바르지 않은 경우 (dict가 아니거나 필수 필드 누락)
            logger.error("[MCP 응답 검증 실패] %s", e)
            return
        except Exception as e:
            logger.error("[MCP 호출 오류] %s", e)
            return

        session_id = mcp_result["sessionId"]

        # 단계 2: 세션 매니저에 등록 + 활성화
        self.sessions.create(session_id, self.current_user_type)
        self.sessions.activate(session_id, service_id)

        # 단계 3: 프론트에 페이지 이동 명령
        success = self.ui.send_command(
            session_id, "MOVE_PAGE", {
                "serviceId": service_id,
                "userType": self.current_user_type,
                "settings": config.USER_CONFIGS[self.current_user_type],
            }
        )

        if success:
            logger.info("서비스 진입: %d (세션: %s, 모드: %s)",
                        service_id, session_id, self.current_user_type)
        else:
            logger.warning("페이지 이동 명령 전송 실패 — 대기 큐 보관 (세션: %s)", session_id)

    # ═════════════════════════════════════════════
    #  프론트 이벤트 수신 핸들러 (양방향)
    # ═════════════════════════════════════════════
    def _on_user_touch(self, payload: dict):
        """프론트에서 사용자 터치/입력 이벤트 수신 → 유휴 타이머 리셋 + 세션 활동 갱신"""
        self._reset_idle_timer()
        session_id = payload.get("data", {}).get("sessionId")
        if session_id:
            self.sessions.touch(session_id)
            logger.info("사용자 활동 수신 (세션: %s)", session_id)

    def _on_service_complete(self, payload: dict):
        """프론트에서 서비스 완료 통보 수신"""
        session_id = payload.get("data", {}).get("sessionId")
        if session_id:
            self.sessions.complete(session_id)
            logger.info("서비스 완료 수신 (세션: %s)", session_id)
        # 완료 후 홈 복귀
        self._return_to_home()

    def _on_ui_ack(self, payload: dict):
        """프론트가 UI 변경 명령 적용 완료를 알림"""
        action = payload.get("data", {}).get("appliedAction")
        logger.info("프론트 ACK 수신: %s 적용 완료", action)

    def _on_user_cancel(self, payload: dict):
        """사용자가 서비스 도중 취소/뒤로가기"""
        session_id = payload.get("data", {}).get("sessionId")
        if session_id:
            self.sessions.fail(session_id)
            logger.info("사용자 취소 (세션: %s)", session_id)
        self._return_to_home()

    def _on_session_timeout(self, session):
        """세션 매니저가 만료 세션을 감지했을 때 호출"""
        logger.warning("세션 만료 처리: %s — 홈 복귀", session.session_id)
        self.ui.send_command(session.session_id, "SESSION_EXPIRED", {
            "message": "시간이 초과되었습니다. 처음 화면으로 돌아갑니다."
        })
        self._return_to_home()

    # ═════════════════════════════════════════════
    #  유휴(Idle) 타이머
    # ═════════════════════════════════════════════
    def _reset_idle_timer(self):
        """입력이 있을 때마다 호출 — 타이머 재시작"""
        self._cancel_idle_timer()
        if self._loop is None:
            return

        # 경고 타이머 (예: 45초 후)
        self._warning_handle = self._loop.call_later(
            config.IDLE_WARNING_SEC,
            self._on_idle_warning
        )
        # 최종 복귀 타이머 (예: 60초 후)
        self._idle_handle = self._loop.call_later(
            config.IDLE_TIMEOUT_SEC,
            self._on_idle_timeout
        )

    def _cancel_idle_timer(self):
        if self._warning_handle:
            self._warning_handle.cancel()
            self._warning_handle = None
        if self._idle_handle:
            self._idle_handle.cancel()
            self._idle_handle = None

    def _on_idle_warning(self):
        """유휴 경고 — 프론트에 '곧 초기화됩니다' 팝업 표시"""
        remaining = config.IDLE_TIMEOUT_SEC - config.IDLE_WARNING_SEC
        self.ui.send_command(None, "IDLE_WARNING", {
            "message": f"{remaining}초 후 처음 화면으로 돌아갑니다.",
            "remainingSec": remaining
        })
        logger.info("유휴 경고 전송 (잔여 %d초)", remaining)

    def _on_idle_timeout(self):
        """유휴 타임아웃 — 모든 활성 세션 만료 처리 후 홈 복귀"""
        logger.info("유휴 타임아웃 — 전체 초기화 시작")

        # 활성 세션 모두 타임아웃 처리
        for sid in self.sessions.get_active_session_ids():
            self.sessions.fail(sid)

        self._return_to_home()

    # ─────────────────────────────────────────────
    # 홈 화면 복귀 (공통)
    # ─────────────────────────────────────────────
    def _return_to_home(self):
        """NORMAL 모드로 복귀 + 홈 화면 이동 명령"""
        self.current_user_type = "NORMAL"
        self.ui.adapt_mode("NORMAL")
        self.ui.send_command(None, "GO_HOME", {
            "message": "처음 화면으로 돌아갑니다."
        })
        self._reset_idle_timer()
        logger.info("홈 화면 복귀 완료 (NORMAL 모드)")


# ─────────────────────────────────────────────────
# 실행
# ─────────────────────────────────────────────────
async def main():
    controller = KioskMainController()
    await controller.start()

    try:
        # 운영 시 계속 대기
        await asyncio.Event().wait()
    finally:
        await controller.shutdown()


if __name__ == "__main__":
    asyncio.run(main())