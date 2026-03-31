# config.py

# ──────────────────────────────────────────────
# STOMP 메시지 브로커 설정
# ──────────────────────────────────────────────
STOMP_HOST = "localhost"
STOMP_PORT = 61613
STOMP_RECONNECT_DELAY = 3
STOMP_MAX_RECONNECT_TRIES = 10

# STOMP 구독 경로 (프론트 → 백엔드)
STOMP_SUB_FRONT_EVENTS = "/topic/front/events"
STOMP_SUB_FRONT_ACK    = "/topic/front/ack"

# ──────────────────────────────────────────────
# MCP 서버 설정
# ──────────────────────────────────────────────
MCP_SERVER_PATH = "./mcp_server.py"

# ──────────────────────────────────────────────
# 서비스 ID 상수 서비스별로 추가예정
# ──────────────────────────────────────────────
SERVICE_ID_REGISTRATION = 101
SERVICE_ID_CERTIFICATE  = 102

# ──────────────────────────────────────────────
# 세션 설정
# ──────────────────────────────────────────────
SESSION_TIMEOUT_SEC      = 300   # 세션 최대 유지 시간 (5분)
SESSION_CLEANUP_INTERVAL = 30    # 만료 세션 정리 주기 (초)

# ──────────────────────────────────────────────
# 유휴(Idle) 타이머 설정
# ──────────────────────────────────────────────
IDLE_TIMEOUT_SEC  = 60           # 무입력 시 홈 복귀까지 (초)
IDLE_WARNING_SEC  = 45           # 복귀 전 경고 표시 시점 (초)

# ──────────────────────────────────────────────
# 사용자 유형별 자동 UI 설정 데이터
# ──────────────────────────────────────────────
USER_CONFIGS = {
    "ELDERLY": {
        "largeFont": True,
        "highContrast": True,
        "simpleMode": True,
        "lowScreenMode": False,
        "fontSize": "24px"
    },
    "WHEELCHAIR": {
        "largeFont": False,
        "highContrast": False,
        "simpleMode": False,
        "lowScreenMode": True,
        "fontSize": "20px"
    },
    "NORMAL": {
        "largeFont": False,
        "highContrast": False,
        "simpleMode": False,
        "lowScreenMode": False,
        "fontSize": "16px"
    }
}