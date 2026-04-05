import sys

# 아주 단순한 표준 입출력 기반의 가짜 서버
def mock_mcp_server():
    # 백엔드가 연결되었을 때 에러가 나지 않도록 무한 대기
    try:
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            # 실제 MCP 프로토콜 대신 그냥 무시하거나 로그만 남김
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    mock_mcp_server()