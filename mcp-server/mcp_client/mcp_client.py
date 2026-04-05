# mcp_client.py
import asyncio
import logging
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
import config

logger = logging.getLogger(__name__)


class MCPError(Exception):
    """MCP 서비스 호출 관련 커스텀 예외"""
    pass


class MCPToolManager:
    def __init__(self):
        self.server_params = StdioServerParameters(
            command="python",
            args=[config.MCP_SERVER_PATH]
        )
        self._session: ClientSession | None = None
        self._read = None
        self._write = None
        self._lock = asyncio.Lock()
        self._context_manager = None

    # ── 연결 ────────────────────────────────────
    async def connect(self):
        """MCP 서버와 세션을 열고 멤버로 유지"""
        if self._session is not None:
            return

        try:
            self._context_manager = stdio_client(self.server_params)
            self._read, self._write = await self._context_manager.__aenter__()

            self._session = ClientSession(self._read, self._write)
            await self._session.__aenter__()
            await self._session.initialize()
            logger.info("MCP 서버 연결 성공")
        except Exception as e:
            await self._cleanup()
            raise ConnectionError(f"MCP 서버 연결 실패: {e}")

    # ── 정리 ────────────────────────────────────
    async def _cleanup(self):
        """내부 리소스 안전하게 정리"""
        try:
            if self._session:
                await self._session.__aexit__(None, None, None)
        except Exception:
            pass
        try:
            if self._context_manager:
                await self._context_manager.__aexit__(None, None, None)
        except Exception:
            pass
        self._session = None
        self._read = None
        self._write = None
        self._context_manager = None

    # ── 서비스 호출 ─────────────────────────────
    async def call_service(
        self,
        tool_name: str,
        arguments: dict,
        max_retries: int = 2,
        required_fields: list[str] | None = None,
    ) -> dict:
        """
        MCP 서버의 특정 도구를 호출하고 응답을 검증한 뒤 반환한다.

        Parameters
        ----------
        tool_name : str
            호출할 MCP 도구 이름 (예: "start_session")
        arguments : dict
            도구에 전달할 인자
        max_retries : int
            최대 재시도 횟수 (기본 2)
        required_fields : list[str] | None
            ★ 응답 dict에 반드시 존재해야 하는 키 목록.
              None이면 검증을 건너뛴다.
              예: ["sessionId"] → 응답에 sessionId가 없으면 MCPError 발생

        Returns
        -------
        dict
            MCP 서버가 반환한 결과 dict

        Raises
        ------
        ConnectionError
            max_retries 횟수 내에 연결·호출 모두 실패한 경우
        MCPError
            응답은 받았으나 형식이 올바르지 않은 경우
        """
        async with self._lock:
            last_error = None

            for attempt in range(1, max_retries + 1):
                try:
                    # 세션이 없으면 연결 시도
                    if self._session is None:
                        await self.connect()

                    raw_result = await self._session.call_tool(tool_name, arguments)

                    # ★ 응답 검증
                    validated = self._validate_result(
                        tool_name, raw_result, required_fields
                    )
                    return validated

                except MCPError:
                    # 검증 실패는 재시도해도 의미 없으므로 즉시 전파
                    raise

                except Exception as e:
                    last_error = e
                    logger.warning(
                        "MCP 호출 실패 (시도 %d/%d) [%s]: %s",
                        attempt, max_retries, tool_name, e
                    )
                    await self._cleanup()

                    if attempt < max_retries:
                        await asyncio.sleep(1)

            raise ConnectionError(
                f"MCP 서비스 '{tool_name}' 호출 {max_retries}회 실패: {last_error}"
            )

    # ══════════════════════════════════════════════
    #  ★ 응답 검증
    # ══════════════════════════════════════════════
    @staticmethod
    def _validate_result(
        tool_name: str,
        raw_result,
        required_fields: list[str] | None,
    ) -> dict:
        """
        MCP 응답을 dict로 변환하고 필수 필드가 존재하는지 확인한다.

        Parameters
        ----------
        tool_name : str
            호출한 도구 이름 (에러 메시지용)
        raw_result
            MCP 서버가 반환한 원시 결과
        required_fields : list[str] | None
            필수 필드 목록. None이면 검증 없이 그대로 반환.

        Returns
        -------
        dict

        Raises
        ------
        MCPError
            dict가 아니거나 필수 필드가 누락된 경우
        """
        # ── 타입 체크 ──────────────────────────
        if raw_result is None:
            raise MCPError(
                f"MCP '{tool_name}' 응답이 None입니다."
            )

        if not isinstance(raw_result, dict):
            raise MCPError(
                f"MCP '{tool_name}' 응답이 dict가 아닙니다: "
                f"type={type(raw_result).__name__}, value={str(raw_result)[:200]}"
            )

        # ── 필수 필드 검증 ─────────────────────
        if required_fields:
            missing = [f for f in required_fields if f not in raw_result]
            if missing:
                raise MCPError(
                    f"MCP '{tool_name}' 응답에 필수 필드 누락: {missing}  "
                    f"(수신 키: {list(raw_result.keys())})"
                )

        logger.debug("MCP '%s' 응답 검증 통과: %s", tool_name, list(raw_result.keys()))
        return raw_result

    # ── 종료 ────────────────────────────────────
    async def disconnect(self):
        """앱 종료 시 명시적으로 호출"""
        async with self._lock:
            await self._cleanup()
            logger.info("MCP 서버 연결 종료")