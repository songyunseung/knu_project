import asyncio
import json
import logging
from typing import Any

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

    async def connect(self):
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

    async def _cleanup(self):
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

    async def call_service(
        self,
        tool_name: str,
        arguments: dict,
        max_retries: int = 2,
        required_fields: list[str] | None = None,
    ) -> dict:
        async with self._lock:
            last_error = None

            for attempt in range(1, max_retries + 1):
                try:
                    if self._session is None:
                        await self.connect()

                    raw_result = await self._session.call_tool(tool_name, arguments)
                    parsed_result = self._extract_result_dict(tool_name, raw_result)
                    validated = self._validate_result(
                        tool_name, parsed_result, required_fields
                    )
                    return validated

                except MCPError:
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

    @staticmethod
    def _extract_result_dict(tool_name: str, raw_result: Any) -> dict:
        if raw_result is None:
            raise MCPError(f"MCP '{tool_name}' 응답이 None입니다.")

        if isinstance(raw_result, dict):
            return raw_result

        if isinstance(raw_result, str):
            try:
                parsed = json.loads(raw_result)
            except json.JSONDecodeError as e:
                raise MCPError(
                    f"MCP '{tool_name}' 문자열 응답 JSON 파싱 실패: {e}"
                ) from e
            if isinstance(parsed, dict):
                return parsed
            raise MCPError(
                f"MCP '{tool_name}' 문자열 응답이 dict JSON이 아닙니다: {type(parsed).__name__}"
            )

        content = getattr(raw_result, "content", None)
        if content:
            for item in content:
                text = getattr(item, "text", None)
                if not isinstance(text, str):
                    continue
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    return parsed

        raise MCPError(
            f"MCP '{tool_name}' 응답에서 dict 추출 실패: "
            f"type={type(raw_result).__name__}, value={str(raw_result)[:200]}"
        )

    @staticmethod
    def _validate_result(
        tool_name: str,
        parsed_result: dict,
        required_fields: list[str] | None,
    ) -> dict:
        if not isinstance(parsed_result, dict):
            raise MCPError(
                f"MCP '{tool_name}' 응답이 dict가 아닙니다: "
                f"type={type(parsed_result).__name__}, value={str(parsed_result)[:200]}"
            )

        if required_fields:
            missing = [f for f in required_fields if f not in parsed_result]
            if missing:
                raise MCPError(
                    f"MCP '{tool_name}' 응답에 필수 필드 누락: {missing}  "
                    f"(수신 키: {list(parsed_result.keys())})"
                )

        logger.debug("MCP '%s' 응답 검증 통과: %s", tool_name, list(parsed_result.keys()))
        return parsed_result

    async def disconnect(self):
        async with self._lock:
            await self._cleanup()
            logger.info("MCP 서버 연결 종료")
