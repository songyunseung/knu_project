# 🖥️ MCP Client & 인터페이스 통합 모듈

> 베리어프리 키오스크 프로젝트 --- MCP 서버와의 실시간 통신 및 Spring
> WebSocket 기반 프론트엔드 UI 제어를 담당하는 클라이언트 모듈입니다.

------------------------------------------------------------------------

## 📁 프로젝트 구조

    ├── main.py
    ├── stomp_manager.py
    ├── mcp_client.py
    ├── session_manager.py
    ├── intent_analyzer.py
    ├── config.py
    └── README.md

------------------------------------------------------------------------

## ⚙️ 모듈별 역할

### main.py

전체 흐름을 조율하는 중앙 컨트롤러입니다.

### stomp_manager.py

Spring WebSocket endpoint에 연결 후 STOMP 프레임 송수신

### mcp_client.py

MCP 서버와 통신

### session_manager.py

세션 상태 관리

### intent_analyzer.py

AI 응답 파싱

------------------------------------------------------------------------

## 🔄 변경사항

-   raw STOMP → WebSocket 방식 전환
-   endpoint: ws://localhost:8080/ws
-   broker: /topic

------------------------------------------------------------------------

## 🚀 실행 방법

``` bash
./gradlew bootRun
python main.py
```

------------------------------------------------------------------------

## 📦 의존성

``` bash
pip install websocket-client mcp
```
