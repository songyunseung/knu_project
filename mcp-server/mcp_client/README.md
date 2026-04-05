# 🖥️ MCP Client & 인터페이스 통합 모듈

> 베리어프리 키오스크 프로젝트 — MCP 서버와의 실시간 통신 및 프론트엔드 UI 제어를 담당하는 클라이언트 모듈입니다.

---

## 📁 프로젝트 구조

```
├── main.py               # 키오스크 메인 컨트롤러 (전체 흐름 조율)
├── stomp_manager.py       # STOMP 기반 프론트엔드 양방향 통신
├── mcp_client.py          # MCP 서버 연결 및 도구 호출 클라이언트
├── session_manager.py     # 세션 생명주기 관리
├── intent_analyzer.py     # AI 응답 파싱 및 의도 분석
├── config.py              # 전역 설정값
└── README.md
```

---

## ⚙️ 모듈별 역할

### `main.py` — KioskMainController

전체 흐름을 조율하는 중앙 컨트롤러입니다.

- 외부 트리거 수신 (`CHANGE_MODE`, `VOICE_INPUT`, `TOUCH_SERVICE`)
- MCP 세션 생성 → 세션 등록 → 프론트 페이지 이동 명령
- 프론트 이벤트 핸들러 등록 및 수신 처리
- 유휴(Idle) 타이머 관리 (경고 → 타임아웃 2단계)

### `stomp_manager.py` — UIController

STOMP 프로토콜 기반으로 프론트엔드와 양방향 통신합니다.

- 연결/재연결 (지수 백오프 + 최대 재시도 제한)
- 대기 큐: 연결 끊김 시 메시지 보관, 재연결 후 자동 플러시
- 이벤트 핸들러 레지스트리: action 기반 메시지 디스패치
- **스레드 안전 브릿지**: STOMP 리스너 스레드 → asyncio 루프

### `mcp_client.py` — MCPToolManager

MCP 서버와의 연결 및 도구 호출을 담당합니다.

- 자동 연결/재연결 (lazy connect + 재시도)
- **응답 검증**: 타입 체크 + 필수 필드 검증 (`required_fields`)
- `MCPError` 커스텀 예외로 연결 실패와 응답 오류 구분

### `session_manager.py` — SessionManager

세션 상태를 추적하고 만료 세션을 자동 정리합니다.

- 상태 전이: `WAITING` → `ACTIVE` → `COMPLETED` / `TIMEOUT` / `ERROR`
- 백그라운드 정리 루프 (주기: `SESSION_CLEANUP_INTERVAL`)
- 외부 타임아웃 콜백 주입 지원

### `intent_analyzer.py` — IntentAnalyzer

AI 서버의 원시 응답을 파싱하여 서비스 ID와 사용자 유형을 결정합니다.

- 키워드 → 서비스 ID 매핑 (`등본`→102, `전입`→101 등)
- 키워드 → 사용자 유형 힌트 (`어르신`→ELDERLY, `휠체어`→WHEELCHAIR)

---

## 🔄 최근 변경사항 (v0.2.0)

### 1. STOMP 스레드 → asyncio 스레드 안전성 확보

**문제**: `stomp.py` 라이브러리의 리스너 콜백(`on_message`)은 별도 스레드에서 실행되는데, 핸들러 내부에서 `asyncio.loop.call_later` 등 루프 의존 코드를 직접 호출하면 스레드 안전성이 보장되지 않았습니다.

**해결**:

- `UIController.__init__`에서 즉시 연결하던 방식을 `connect(loop)` 메서드로 분리
- `main.py`의 `start()`에서 `self.ui.connect(loop=self._loop)`으로 asyncio 루프 주입
- `_dispatch_message`에서 `loop.call_soon_threadsafe()`를 통해 핸들러 실행을 asyncio 루프 스레드에 위임
- 코루틴 핸들러는 `create_task`로, 동기 핸들러도 루프 스레드에서 실행

```python
# stomp_manager.py — _dispatch_message 핵심 로직

if asyncio.iscoroutinefunction(handler):
    # 코루틴 핸들러 → asyncio 루프에 태스크로 스케줄링
    def _schedule_coro():
        self._loop.create_task(
            self._safe_async_handler(action, handler, payload)
        )
    self._loop.call_soon_threadsafe(_schedule_coro)
else:
    # 동기 핸들러 → asyncio 루프 스레드에서 실행
    def _run_sync():
        handler(payload)
    self._loop.call_soon_threadsafe(_run_sync)
```

### 2. MCP 응답 검증 + 로깅 통일

**문제**: `mcp_result["sessionId"]`를 검증 없이 직접 접근하여, MCP 서버가 예상과 다른 응답을 반환하면 `KeyError`로 크래시가 발생했습니다. 또한 `print()`와 `logging`이 혼용되고 있었습니다.

**해결**:

- `call_service`에 `required_fields` 파라미터 추가
- `_validate_result`에서 None 체크, dict 타입 체크, 필수 필드 누락 체크 수행
- 검증 실패 시 `MCPError` 발생 (재시도 없이 즉시 전파)
- `print()` 전부 `logging` 모듈로 교체

```python
# main.py — 변경 전
mcp_result = await self.mcp.call_service(
    "start_session", {"userType": self.current_user_type}
)
session_id = mcp_result["sessionId"]  # ← KeyError 위험

# main.py — 변경 후
mcp_result = await self.mcp.call_service(
    "start_session",
    {"userType": self.current_user_type},
    required_fields=["sessionId"],       # ← 필수 필드 명시
)
session_id = mcp_result["sessionId"]     # ← 검증 통과 보장
```

---

## 🔗 팀별 연동 가이드

### 1번 팀 — AI & LLM Server

| 항목 | 내용 |
|------|------|
| 영향도 | 낮음 (직접적인 코드 변경 없음) |
| 확인 필요 | AI 응답 JSON 스키마가 현재 파서와 일치하는지 확인 |

`intent_analyzer.py`가 기대하는 AI 응답 형식:

```json
{
  "intent": "ISSUE",
  "target": "등본",
  "confidence": 0.92,
  "extra": "휠체어 이용자입니다"
}
```

- `confidence` 범위: `0.0 ~ 1.0` (임계값 `0.6` 미만이면 무시)
- `target` 필드에 서비스 키워드 포함 필요: `등본`, `초본`, `전입`, `전출`
- `extra` 등 문자열 필드에 사용자 유형 힌트 포함 가능: `어르신`, `노인`, `휠체어`, `낮은`

---

### 2번 팀 — MCP Server & 하드웨어

| 항목 | 내용 |
|------|------|
| 영향도 | **높음** — MCP 응답 검증 로직 추가 |
| 확인 필요 | `start_session` 도구의 응답에 `sessionId` 필수 포함 |

**필수 확인사항:**

- `start_session` 도구 호출 시 응답이 반드시 `dict` 타입이어야 합니다.
- 응답에 `sessionId` 키가 반드시 포함되어야 합니다.
- 위 조건 미충족 시 `MCPError` 발생 → 서비스 진입 중단

```
✅ 정상 응답 예시
{"sessionId": "sess-abc-123", "status": "created"}

❌ 오류 발생 케이스
{"status": "created"}                    → sessionId 누락 → MCPError
None                                     → 응답 자체가 None → MCPError
"sess-abc-123"                           → dict가 아닌 str → MCPError
```

**신규 도구 추가 시 권장사항:**

클라이언트 측에서 `required_fields`를 도구별로 명시할 예정이므로, 도구별 응답 스키마를 문서화해주시면 연동이 수월합니다.

---

### 3번 팀 — Spring 백엔드 & DB

| 항목 | 내용 |
|------|------|
| 영향도 | 낮음 (직접적인 코드 변경 없음) |
| 확인 필요 | 세션 ID 연동 방식 및 상태 전이 시 백엔드 처리 |

MCP 서버가 발급하는 `sessionId`가 백엔드 세션/트랜잭션 ID와 연동되는 경우, 아래 상태 전이 흐름과 각 상태에서 백엔드 측 처리가 필요한지 확인 부탁드립니다.

```
WAITING ──→ ACTIVE ──→ COMPLETED (정상 종료)
                   ├──→ TIMEOUT   (시간 초과)
                   └──→ ERROR     (취소/오류)
```

- `TIMEOUT` / `ERROR` 시 백엔드 롤백이나 리소스 정리가 필요한지 논의 필요

---

### 5번 팀 — Front-end & HCI

| 항목 | 내용 |
|------|------|
| 영향도 | **중간** — 메시지 포맷 변경 없음, 내부 디스패치 구조 변경 |
| 확인 필요 | STOMP 연결 타이밍, action 필드 정합성 |

**프론트 → 백엔드 (이벤트 전송)**

프론트에서 STOMP로 보내는 메시지의 `action` 필드가 핸들러 라우팅 키입니다.

| action | 설명 | payload 예시 |
|--------|------|-------------|
| `USER_TOUCH` | 사용자 터치/입력 활동 | `{"data": {"sessionId": "..."}}` |
| `SERVICE_COMPLETE` | 서비스 정상 완료 | `{"data": {"sessionId": "..."}}` |
| `UI_ACK` | UI 변경 적용 완료 응답 | `{"data": {"appliedAction": "ADAPT_UI"}}` |
| `USER_CANCEL` | 사용자 취소/뒤로가기 | `{"data": {"sessionId": "..."}}` |

**백엔드 → 프론트 (명령 수신)**

| action | 설명 | 수신 토픽 |
|--------|------|----------|
| `ADAPT_UI` | UI 모드 변경 (글씨 크기, 대비 등) | `/topic/ui/global` |
| `MOVE_PAGE` | 서비스 페이지 이동 | `/topic/ui/{sessionId}` |
| `GO_HOME` | 홈 화면 복귀 | `/topic/ui/global` |
| `IDLE_WARNING` | 유휴 경고 팝업 표시 | `/topic/ui/global` |
| `SESSION_EXPIRED` | 세션 만료 알림 | `/topic/ui/{sessionId}` |


action 조건문 참조예시

onConnect: () => {
  client.subscribe('/topic/ui/global', (message) => {
    const data = JSON.parse(message.body);
    // action이 'ADAPT_UI'일 때만 세팅 변경
    if (data.action === 'ADAPT_UI') {
      setAccessibility(data.data.settings);
    } else if (data.action === 'GO_HOME') {
      // 홈으로 이동하는 로직 등 추가 가능
    }
  });
}

**주의사항:**

- `UIController`가 생성 시 즉시 연결하지 않고 `connect()` 호출 시점에 연결하도록 변경됨
- 프론트에서 STOMP 연결 타이밍에 의존하는 로직이 있다면 서버 기동 순서 확인 필요
- 메시지 포맷 자체는 변경 없음

---

## 🛠️ 설정값 참조 (`config.py`)

| 설정 | 값 | 설명 |
|------|---|------|
| `STOMP_HOST` | `localhost` | STOMP 브로커 주소 |
| `STOMP_PORT` | `61613` | STOMP 브로커 포트 |
| `STOMP_RECONNECT_DELAY` | `3` | 재연결 초기 대기(초) |
| `STOMP_MAX_RECONNECT_TRIES` | `10` | 최대 재연결 시도 |
| `SESSION_TIMEOUT_SEC` | `300` | 세션 최대 유지 시간 (5분) |
| `SESSION_CLEANUP_INTERVAL` | `30` | 만료 세션 정리 주기 (초) |
| `IDLE_TIMEOUT_SEC` | `60` | 무입력 시 홈 복귀까지 (초) |
| `IDLE_WARNING_SEC` | `45` | 복귀 전 경고 표시 시점 (초) |

---

## 🚀 실행 방법

```bash
python main.py
```

> 실제 운영 시 `main()` 함수 내의 `await asyncio.Event().wait()` 주석을 해제하여 이벤트 루프가 지속 실행되도록 합니다.

---

## 📋 의존성

- `stomp.py` — STOMP 프로토콜 클라이언트
- `mcp` — MCP(Model Context Protocol) SDK

```bash
pip install stomp.py mcp
```
