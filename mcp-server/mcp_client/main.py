import asyncio
import logging

import config
from stomp_manager import UIController
from mcp_client import MCPToolManager, MCPError
from intent_analyzer import IntentAnalyzer
from session_manager import SessionManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("kiosk.main")


class KioskMainController:
    """
    MCP Client 측 오케스트레이터.

    변경 사항
    - 프론트와 충돌하는 앱 전역 idle 타이머 제거
    - 홈 복귀 시 NORMAL 모드 강제 초기화 제거
    - mode 상태와 홈 이동 로직 분리
    - 세션 timeout은 SessionManager만 담당
    """

    def __init__(self):
        self.ui = UIController()
        self.mcp = MCPToolManager()
        self.ai = IntentAnalyzer()
        self.sessions = SessionManager()
        self.current_user_type = "NORMAL"
        self._loop: asyncio.AbstractEventLoop | None = None

        self.ui.register_handler("USER_TOUCH", self._on_user_touch)
        self.ui.register_handler("SERVICE_COMPLETE", self._on_service_complete)
        self.ui.register_handler("UI_ACK", self._on_ui_ack)
        self.ui.register_handler("USER_CANCEL", self._on_user_cancel)

        self.sessions.set_timeout_callback(self._on_session_timeout)

    async def start(self):
        self._loop = asyncio.get_running_loop()
        self.ui.connect(loop=self._loop)
        self.sessions.start()
        logger.info("키오스크 컨트롤러 기동 완료")

    async def shutdown(self):
        await self.sessions.stop()
        await self.mcp.disconnect()
        self.ui.disconnect()
        logger.info("키오스크 컨트롤러 종료 완료")

    async def handle_request(self, trigger_type, data):
        if trigger_type == "CHANGE_MODE":
            self._change_mode(data)
        elif trigger_type == "VOICE_INPUT":
            await self._handle_voice(data)
        elif trigger_type == "TOUCH_SERVICE":
            await self._handle_touch(data)
        else:
            logger.warning("알 수 없는 trigger_type: %s", trigger_type)

    def _change_mode(self, user_type: str):
        if user_type not in config.USER_CONFIGS:
            logger.warning("미지원 사용자 유형 '%s' → NORMAL 대체", user_type)
            user_type = "NORMAL"

        self.current_user_type = user_type
        self.ui.adapt_mode(self.current_user_type)
        logger.info("모드 변경: %s", self.current_user_type)

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

    async def _handle_touch(self, service_id):
        if service_id is None:
            logger.warning("service_id 비어 있음 — 요청 무시")
            return
        await self._execute_service(service_id)

    async def _execute_service(self, service_id):
        try:
            mcp_result = await self.mcp.call_service(
                "start_session",
                {"userType": self.current_user_type},
                required_fields=["sessionId"],
            )
        except ConnectionError as e:
            logger.error("[MCP 연결 실패] %s", e)
            return
        except MCPError as e:
            logger.error("[MCP 응답 검증 실패] %s", e)
            return
        except Exception as e:
            logger.error("[MCP 호출 오류] %s", e)
            return

        session_id = mcp_result["sessionId"]

        self.sessions.create(session_id, self.current_user_type)
        self.sessions.activate(session_id, service_id)

        settings = mcp_result.get("settings") or config.USER_CONFIGS[self.current_user_type]

        success = self.ui.send_command(
            session_id, "MOVE_PAGE", {
                "serviceId": service_id,
                "userType": self.current_user_type,
                "settings": settings,
            }
        )

        if success:
            logger.info(
                "서비스 진입: %d (세션: %s, 모드: %s)",
                service_id, session_id, self.current_user_type
            )
        else:
            logger.warning("페이지 이동 명령 전송 실패 — 대기 큐 보관 (세션: %s)", session_id)

    def _on_user_touch(self, payload: dict):
        session_id = payload.get("data", {}).get("sessionId")
        if session_id:
            self.sessions.touch(session_id)
            logger.info("사용자 활동 수신 (세션: %s)", session_id)

    def _on_service_complete(self, payload: dict):
        session_id = payload.get("data", {}).get("sessionId")
        if session_id:
            self.sessions.complete(session_id)
            logger.info("서비스 완료 수신 (세션: %s)", session_id)
        self._return_to_home()

    def _on_ui_ack(self, payload: dict):
        action = payload.get("data", {}).get("appliedAction")
        logger.info("프론트 ACK 수신: %s 적용 완료", action)

    def _on_user_cancel(self, payload: dict):
        session_id = payload.get("data", {}).get("sessionId")
        if session_id:
            self.sessions.fail(session_id)
            logger.info("사용자 취소 (세션: %s)", session_id)
        self._return_to_home()

    def _on_session_timeout(self, session):
        logger.warning("세션 만료 처리: %s — 홈 복귀", session.session_id)
        self.ui.send_command(session.session_id, "SESSION_EXPIRED", {
            "message": "시간이 초과되었습니다. 처음 화면으로 돌아갑니다."
        })
        self._return_to_home()

    def _return_to_home(self):
        """
        홈 화면 이동만 수행.
        - mode를 NORMAL로 강제 초기화하지 않음
        - ADAPT_UI(NORMAL)를 자동 송신하지 않음
        """
        self.ui.send_command(None, "GO_HOME", {
            "message": "처음 화면으로 돌아갑니다."
        })
        logger.info("홈 화면 복귀 완료 (모드 유지: %s)", self.current_user_type)


async def main():
    controller = KioskMainController()
    await controller.start()

    try:
        await asyncio.Event().wait()
    finally:
        await controller.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
#배포/운영단계에서는 end_seesion추가해야 안정