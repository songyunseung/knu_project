# mcp-server/server.py
from mcp.server.fastmcp import FastMCP

# 1. MCP 서버 초기화 (서버 이름 설정)
mcp = FastMCP("Barrier-Free-Kiosk-Agent")

# 2. 도구 정의: 키오스크 높이 조절
@mcp.tool()
def adjust_kiosk_height(target_height_cm: int) -> str:
    """
    사용자의 눈높이에 맞춰 키오스크의 물리적 높이를 조절합니다.
    target_height_cm: 조절하고자 하는 목표 높이 (범위: 80 ~ 120cm)
    """
    # 실제 구현 시에는 여기서 하드웨어 제어 모듈이나 
    # Spring Boot API(3번 담당자)로 신호를 보냅니다.
    print(f"[시스템] 키오스크 높이를 {target_height_cm}cm로 조절 중...")
    
    return f"성공: 키오스크 높이가 {target_height_cm}cm로 조정되었습니다."

# 3. 도구 정의: UI 모드 변경 (고대비/큰글씨)
@mcp.tool()
def switch_ui_mode(mode: str) -> str:
    """
    사용자의 특성(고령자, 저시력자 등)에 맞춰 UI 모드를 변경합니다.
    mode: 'high_contrast' (고대비), 'large_text' (큰글씨), 'default' (기본)
    """
    print(f"[시스템] UI를 {mode} 모드로 전환합니다.")
    
    # 여기서 5번(Front) 담당자가 만든 UI로 신호를 보냅니다.
    return f"성공: 화면이 {mode} 모드로 변경되었습니다."

if __name__ == "__main__":
    # 서버 실행
    mcp.run()
