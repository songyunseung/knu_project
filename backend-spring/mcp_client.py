import asyncio
import json
import stomp
import datetime
from mcp import ClientSession
from mcp.client.stdio import stdio_client

# --- 설정 정보 ---
SPRING_HOST = "localhost"
SPRING_PORT = 8080
STOMP_TOPIC_PREFIX = "/topic/ui"

class KioskMasterController:
    def __init__(self):
        # 1. 역할 5(Frontend)와 연결될 STOMP 클라이언트 초기화
        try:
            self.conn = stomp.Connection([(SPRING_HOST, SPRING_PORT)])
            self.conn.connect(wait=True)
            print("✅ [역할 4] STOMP Broker 연결 성공 (Frontend 중계 준비)")
        except Exception as e:
            print(f"❌ STOMP 연결 실패: {e}")

    async def process_kiosk_event(self, user_voice_input=None, manual_type=None):
        """
        통합 이벤트 처리 로직
        - user_voice_input: 1번(AI)이 분석할 음성 텍스트
        - manual_type: 5번(프론트)에서 직접 누른 버튼 타입 (ELDERLY, WHEELCHAIR 등)
        """
        
        # 2. 역할 2(MCP Server) 실행 및 연결
        server_params = {"command": "python", "args": ["role2_server.py"]}
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as mcp_session:
                await mcp_session.initialize()
                print("🤖 [역할 4] MCP Server(역할 2)와 동기화 완료")

                # --- [STEP 1] 사용자 유형(userType) 결정 로직 ---
                if manual_type:
                    # 사용자가 화면에서 버튼을 직접 선택한 경우 (최우선)
                    print(f"🖱️ [Touch] 사용자가 직접 버튼 클릭: {manual_type}")
                    detected_type = manual_type
                elif user_voice_input:
                    # 사용자가 음성으로 말한 경우 (1번 AI 분석 필요)
                    print(f"🧠 [AI] 음성 분석 중: '{user_voice_input}'")
                    # TODO: 여기서 실제 1번(AI Server) API를 호출합니다.
                    # 임시로 '어르신' 관련 단어가 있으면 ELDERLY로 판단하는 로직 예시
                    detected_type = "ELDERLY" if "어르신" in user_voice_input or "할머니" in user_voice_input else "NORMAL"
                else:
                    # 아무 입력 없이 '시작'만 누른 경우
                    print("🖱️ [Default] 일반 모드(NORMAL)로 시작")
                    detected_type = "NORMAL"

                # --- [STEP 2] 역할 2(MCP)를 통해 백엔드(3번) API 호출 ---
                print(f"📡 [MCP] '{detected_type}' 모드로 세션 생성 요청...")
                api_response = await mcp_session.call_tool(
                    "start_kiosk_session", 
                    arguments={"detected_type": detected_type, "device_id": "KIOSK_01"}
                )

                # --- [STEP 3] 데이터 조합 및 프론트엔드(5번) 중계 ---
                if api_response and "sessionId" in api_response:
                    session_id = api_response["sessionId"]
                    
                    # 5번(프론트)이 바로 쓸 수 있게 규격화된 JSON 생성
                    final_ui_payload = {
                        "sessionId": session_id,
                        "userType": detected_type,
                        "settings": api_response.get("settings", {
                            "largeFont": detected_type == "ELDERLY",
                            "highContrast": detected_type == "ELDERLY",
                            "lowScreenMode": detected_type == "WHEELCHAIR"
                        }),
                        "action": "UI_ADAPTATION",
                        "timestamp": datetime.datetime.now().isoformat()
                    }

                    # STOMP 발행: /topic/ui/{sessionId}
                    destination = f"{STOMP_TOPIC_PREFIX}/{session_id}"
                    self.conn.send(
                        body=json.dumps(final_ui_payload), 
                        destination=destination
                    )
                    print(f"🚀 [Success] 프론트엔드 화면 변경 신호 발송 완료: {destination}")
                    
                    # (추가) 3번 백엔드에 로그 기록 요청
                    await mcp_session.call_tool(
                        "save_interaction_log",
                        arguments={
                            "session_id": session_id,
                            "action_type": "UI_INIT",
                            "action_detail": f"Mode set to {detected_type}"
                        }
                    )
                else:
                    print("❌ [Error] 세션 생성 실패")

    def __del__(self):
        if hasattr(self, 'conn') and self.conn.is_connected():
            self.conn.disconnect()

# --- 실행부 ---
if __name__ == "__main__":
    master = KioskMasterController()
    
    # 테스트 시나리오 선택 (하나만 주석 해제해서 테스트하세요)
    
    # 시나리오 A: 사용자가 화면에서 '어르신 전용' 버튼을 직접 누름
    asyncio.run(master.process_kiosk_event(manual_type="ELDERLY"))
    
    # 시나리오 B: 사용자가 음성으로 말함
    # asyncio.run(master.process_kiosk_event(user_voice_input="할머니가 쓰기 편하게 해줘"))
    
    # 시나리오 C: 그냥 일반 시작 버튼 누름
    # asyncio.run(master.process_kiosk_event())