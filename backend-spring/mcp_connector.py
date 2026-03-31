import httpx
import asyncio
from mcp.server.fastmcp import FastMCP

# 1. MCP 서버 초기화 (이름: Kiosk-Bridge)
mcp = FastMCP("Kiosk-Bridge")

# 백엔드 서버 주소 (Docker로 띄운 Spring Boot)
BACKEND_URL = "http://localhost:8080"
# 1. 세션 시작 (POST /api/session/start)
@mcp.tool()
async def start_kiosk_session(detected_type: str, device_id: str = "KIOSK_01") -> str:
    """
    키오스크 사용 세션을 DB에 생성합니다.
    - detected_type: 사용자 유형 (예: ELDERLY, NORMAL, DISABLED)
    - device_id: 기기 식별자 (기본값: KIOSK_01)
    """
    url = f"{BACKEND_URL}/api/session/start"
    
    # pgAdmin에서 확인한 정합성 기준 데이터
    payload = {
        "detectedType": detected_type, 
        "deviceId": device_id         
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            
            # 응답 상태 확인 (200 OK인지 체크)
            if response.status_code == 200:
                data = response.json()
                return f"✅ 세션 생성 성공! ID: {data.get('session_id')}"
            else:
                # 500 에러 등 발생 시 서버 메시지 반환
                return f"❌ 서버 에러 ({response.status_code}): {response.text}"
                
        except Exception as e:
            return f"⚠️ 통신 실패: {str(e)}"
        
# 2. 세션 종료 (POST /api/session/end)
@mcp.tool()
async def end_kiosk_session(session_id: str) -> str:
    """
    사용자가 자리를 뜰 때 세션을 종료합니다.
    - session_id: 종료할 세션의 고유 ID
    """
    url = f"{BACKEND_URL}/api/session/end"
    payload = {"sessionId": session_id} # 자바 request.get("sessionId") 대응

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                return f"✅ 세션 종료 성공: {session_id}"
            return f"❌ 종료 실패 ({response.status_code})"
        except Exception as e:
            return f"⚠️ 통신 오류: {str(e)}"

# 3. UI 설정 변경 (PUT /api/session/{sessionId}/accessibility)
@mcp.tool()
async def update_ui_accessibility(
    session_id: str, 
    user_type: str = None,
    large_font: bool = True, 
    high_contrast: bool = False,
    voice_guide: bool = False
) -> str:
    """
    사용자의 요구에 맞춰 키오스크 UI 설정을 실시간으로 변경합니다.
    - user_type: ELDERLY, NORMAL 등 (선택 사항)
    - large_font: 큰 글씨 모드 여부
    - high_contrast: 고대비 모드 여부
    - voice_guide: 음성 안내 여부
    """
    # PathVariable 처리
    url = f"{BACKEND_URL}/api/session/{session_id}/accessibility"
    
    # 자바 컨트롤러의 request.get("이름")과 정확히 일치
    payload = {
        "userType": user_type,
        "largeFont": large_font,
        "highContrast": high_contrast,
        "simpleMode": True,      # 기본값 설정
        "voiceGuide": voice_guide,
        "lowScreenMode": False,  # 기본값 설정
        "fontSize": 24 if large_font else 16
    }

    async with httpx.AsyncClient() as client:
        try:
            # PUT 메서드 사용
            response = await client.put(url, json=payload)
            if response.status_code == 200:
                return f"✅ UI 설정 변경 완료 (세션: {session_id})"
            return f"❌ 변경 실패 ({response.status_code}): {response.text}"
        except Exception as e:
            return f"⚠️ 통신 오류: {str(e)}"
# 4. 로그기록 (POST /api/session/log)
@mcp.tool()
async def save_interaction_log(
    session_id: str, 
    action_type: str, 
    action_detail: str, 
    ai_response: str = "", 
    response_time: int = 0
) -> str:
    """사용자의 행동과 AI의 응답을 기록합니다."""
    url = f"{BACKEND_URL}/api/session/log"
    payload = {
        "sessionId": session_id,
        "actionType": action_type,    # 예: "VOICE_INPUT"
        "actionDetail": action_detail, # 예: "주민등록등본 떼줘"
        "aiResponse": ai_response,
        "responseTime": response_time
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        return "✅ 로그 기록 성공" if response.status_code == 200 else "❌ 로그 기록 실패"

# 5. 전체 서비스 목록 조회 (GET /api/services)
@mcp.tool()
async def get_kiosk_services() -> str:
    """
    키오스크에서 제공하는 모든 민원 서비스 목록을 가져옵니다.
    AI는 이 목록을 보고 사용자에게 어떤 서류 발급이 가능한지 안내합니다.
    """
    url = f"{BACKEND_URL}/api/services"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            if response.status_code == 200:
                # 백엔드에서 받은 서비스 리스트(JSON)를 문자열로 반환
                return f"📋 서비스 목록: {response.text}"
            return f"❌ 목록 조회 실패 ({response.status_code})"
        except Exception as e:
            return f"⚠️ 통신 오류: {str(e)}"

# 6. 민원 신청 접수 (POST /api/applications)
@mcp.tool()
async def submit_civil_application(
    session_id: str, 
    service_id: int, 
    details: str = ""
) -> str:
    """
    사용자의 민원 신청을 실제로 접수합니다.
    - session_id: 현재 진행 중인 세션 ID (UUID)
    - service_id: 신청할 서비스 번호 (예: 1)
    - details: 추가 요청 사항 (예: "주민등록번호 뒷자리 포함")
    """
    url = f"{BACKEND_URL}/api/applications"
    
    # 자바 컨트롤러 규격에 맞춘 페이로드 (카멜 케이스 지켜주세요!)
    payload = {
        "sessionId": session_id,
        "serviceId": service_id,
        "applicationDetails": details
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                return f"✅ 민원 접수 성공! (서비스 번호: {service_id})"
            return f"❌ 접수 실패 ({response.status_code}): {response.text}"
        except Exception as e:
            return f"⚠️ 통신 오류: {str(e)}"
        

if __name__ == "__main__":
    # 1. 먼저 세션을 시작하고 ID를 얻었다고 가정
    test_id = "얻어온_세션_ID_값" 
    
    print("--- UI 설정 변경 테스트 ---")
    asyncio.run(update_ui_accessibility(test_id, voice_guide=True))
    
    print("--- 세션 종료 테스트 ---")
    asyncio.run(end_kiosk_session(test_id))
# if __name__ == "__main__":
#     # MCP 서버 실행
#     mcp.run()