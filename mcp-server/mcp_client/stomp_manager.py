import asyncio
import json
import logging
import threading
import time
import uuid
from collections import deque
from datetime import datetime

import websocket

import config

logger = logging.getLogger(__name__)


class UIController:
    """
    Spring WebSocket + STOMP 클라이언트
    - ws://localhost:8080/ws 로 접속
    - CONNECT / SUBSCRIBE / SEND 프레임 직접 처리
    """

    def __init__(self):
        self._connected = False
        self._reconnecting = False
        self._pending_queue: deque = deque(maxlen=100)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._handlers: dict[str, callable] = {}

        self.ws: websocket.WebSocket | None = None
        self._receiver_thread: threading.Thread | None = None
        self._session_id = str(uuid.uuid4())

    # ── 연결 ────────────────────────────────────
    def connect(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop
        self._do_connect()

    def _do_connect(self):
        try:
            logger.info("WebSocket 연결 시도: %s", config.WS_URL)
            self.ws = websocket.WebSocket()
            self.ws.connect(config.WS_URL)

            self._send_frame(
                "CONNECT",
                {
                    "accept-version": "1.2",
                    "host": "localhost",
                    "heart-beat": "10000,10000",
                },
            )

            frame = self._recv_frame_blocking()
            if not frame.startswith("CONNECTED"):
                raise ConnectionError(f"STOMP CONNECT 실패: {frame[:200]}")

            self._connected = True
            logger.info("WebSocket/STOMP 연결 성공")

            self._subscribe_all()
            self._flush_pending_queue()

            self._receiver_thread = threading.Thread(
                target=self._receive_loop,
                daemon=True,
            )
            self._receiver_thread.start()

        except Exception as e:
            logger.error("WebSocket/STOMP 연결 실패: %s", e)
            self._connected = False
            self._schedule_reconnect()

    def _schedule_reconnect(self):
        if self._reconnecting:
            return
        self._reconnecting = True

        def _loop():
            delay = config.WS_RECONNECT_DELAY
            for attempt in range(1, config.WS_MAX_RECONNECT_TRIES + 1):
                if self._connected:
                    break

                logger.info(
                    "WebSocket 재연결 시도 %d/%d (%ds 후)",
                    attempt,
                    config.WS_MAX_RECONNECT_TRIES,
                    delay,
                )
                time.sleep(delay)

                try:
                    self._close_socket()
                    self._do_connect()
                    if self._connected:
                        break
                except Exception as e:
                    logger.warning("재연결 실패: %s", e)
                    delay = min(delay * 2, 30)
            else:
                logger.critical("WebSocket 재연결 최대 시도 초과 — 수동 점검 필요")

            self._reconnecting = False

        threading.Thread(target=_loop, daemon=True).start()

    # ── STOMP 프레임 처리 ───────────────────────
    def _send_frame(self, command: str, headers: dict | None = None, body: str = ""):
        headers = headers or {}
        frame = command + "\n"
        for k, v in headers.items():
            frame += f"{k}:{v}\n"
        frame += "\n"
        frame += body
        frame += "\x00"
        self.ws.send(frame)

    def _recv_frame_blocking(self) -> str:
        chunks = []
        while True:
            data = self.ws.recv()
            if isinstance(data, bytes):
                data = data.decode("utf-8", errors="ignore")
            chunks.append(data)
            joined = "".join(chunks)
            if "\x00" in joined:
                return joined.split("\x00", 1)[0]

    def _parse_frame(self, raw_frame: str):
        raw_frame = raw_frame.replace("\r\n", "\n")
        parts = raw_frame.split("\n\n", 1)
        header_part = parts[0]
        body = parts[1] if len(parts) > 1 else ""

        lines = header_part.split("\n")
        command = lines[0].strip()
        headers = {}

        for line in lines[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip()] = v.strip()

        return command, headers, body

    # ── 수신 루프 ───────────────────────────────
    def _receive_loop(self):
        try:
            while self.ws:
                raw = self._recv_frame_blocking()
                command, headers, body = self._parse_frame(raw)

                if command == "MESSAGE":
                    dest = headers.get("destination", "")
                    try:
                        payload = json.loads(body)
                    except json.JSONDecodeError:
                        logger.warning("수신 메시지 JSON 파싱 실패: %s", body[:200])
                        continue

                    logger.info("수신 ← [%s] action=%s", dest, payload.get("action"))
                    self._dispatch_message(dest, payload)

                elif command == "ERROR":
                    logger.error("STOMP ERROR: %s", body)

                elif command == "\n":
                    # heartbeat
                    pass

        except Exception as e:
            if self._connected:
                logger.warning("WebSocket 연결 끊김 — 자동 재연결 시도: %s", e)
            self._connected = False
            self._schedule_reconnect()

    # ── 구독 ────────────────────────────────────
    def _subscribe_all(self):
        subs = [
            (config.STOMP_SUB_FRONT_EVENTS, "sub-events"),
            (config.STOMP_SUB_FRONT_ACK, "sub-ack"),
        ]
        for dest, sub_id in subs:
            try:
                self._send_frame(
                    "SUBSCRIBE",
                    {
                        "id": sub_id,
                        "destination": dest,
                        "ack": "auto",
                    },
                )
                logger.info("구독 등록: %s", dest)
            except Exception as e:
                logger.error("구독 실패 [%s]: %s", dest, e)

    # ── 핸들러 ──────────────────────────────────
    def register_handler(self, action: str, callback):
        self._handlers[action] = callback
        logger.info("핸들러 등록: action='%s'", action)

    def _dispatch_message(self, destination: str, payload: dict):
        action = payload.get("action")
        handler = self._handlers.get(action)
        if not handler:
            logger.debug("미등록 action 수신 무시: %s", action)
            return

        if self._loop is None or self._loop.is_closed():
            logger.warning("asyncio 루프 미설정 — 현재 스레드에서 직접 실행: %s", action)
            try:
                handler(payload)
            except Exception as e:
                logger.error("핸들러 오류 [%s]: %s", action, e)
            return

        if asyncio.iscoroutinefunction(handler):
            def _schedule_coro():
                self._loop.create_task(self._safe_async_handler(action, handler, payload))
            self._loop.call_soon_threadsafe(_schedule_coro)
        else:
            def _run_sync():
                try:
                    handler(payload)
                except Exception as e:
                    logger.error("핸들러 오류 [%s]: %s", action, e)
            self._loop.call_soon_threadsafe(_run_sync)

    @staticmethod
    async def _safe_async_handler(action: str, handler, payload: dict):
        try:
            await handler(payload)
        except Exception as e:
            logger.error("비동기 핸들러 오류 [%s]: %s", action, e)

    # ── 송신 ────────────────────────────────────
    def _flush_pending_queue(self):
        sent = 0
        while self._pending_queue:
            dest, body = self._pending_queue.popleft()
            try:
                self._send_frame(
                    "SEND",
                    {
                        "destination": dest,
                        "content-type": "application/json",
                    },
                    body,
                )
                sent += 1
            except Exception as e:
                self._pending_queue.appendleft((dest, body))
                logger.warning("큐 플러시 중 전송 실패: %s", e)
                break

        if sent:
            logger.info("대기 큐 메시지 %d건 전송 완료", sent)

    def send_command(self, session_id, action, payload=None) -> bool:
        message = {
            "action": action,
            "timestamp": datetime.now().isoformat(),
            "data": payload or {},
        }
        dest = f"/topic/ui/{session_id}" if session_id else "/topic/ui/global"
        body = json.dumps(message, ensure_ascii=False)

        if not self._connected:
            logger.warning("WebSocket 미연결 — 대기 큐 보관: %s", action)
            self._pending_queue.append((dest, body))
            return False

        try:
            self._send_frame(
                "SEND",
                {
                    "destination": dest,
                    "content-type": "application/json",
                },
                body,
            )
            return True
        except Exception as e:
            logger.error("메시지 전송 오류: %s — 대기 큐 보관", e)
            self._pending_queue.append((dest, body))
            self._connected = False
            self._schedule_reconnect()
            return False

    def adapt_mode(self, user_type) -> bool:
        settings = config.USER_CONFIGS.get(user_type, config.USER_CONFIGS["NORMAL"])
        success = self.send_command(None, "ADAPT_UI", {
            "userType": user_type,
            "settings": settings
        })
        logger.info("UI 모드 송출: %s [%s]", user_type, "성공" if success else "큐 대기")
        return success

    # ── 종료 ────────────────────────────────────
    def _close_socket(self):
        try:
            if self.ws:
                try:
                    self._send_frame("DISCONNECT")
                except Exception:
                    pass
                self.ws.close()
        except Exception:
            pass
        finally:
            self.ws = None

    def disconnect(self):
        self._connected = False
        self._close_socket()
        self._loop = None
        logger.info("WebSocket/STOMP 연결 종료")