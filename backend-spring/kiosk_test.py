import requests

# 1. 주소 확인 (로그 상의 /api/session/start 경로 유지)
url = "http://localhost:8080/api/session/start" 

# 2. 실제 DB 컬럼명(image_8b417f.png)에 맞춘 데이터 구성
data = {
    "detectedType": "ELDERLY",  # DB의 detected_type 컬럼과 매칭
    "deviceId": "KIOSK_01"      # DB의 device_id 컬럼과 매칭
}

try:
    response = requests.post(url, json=data)
    print(f"상태 코드: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ [축하합니다!] 드디어 서버-DB 통합 테스트에 성공했습니다.")
        print("응답 내용:", response.text)
    else:
        print(f"❌ 여전히 에러 발생: {response.text}")
        print("💡 팁: 서버 터미널의 로그(빨간 글씨)를 다시 한번 확인해 주세요.")
        
except Exception as e:
    print(f"❗ 연결 실패: {e}")
