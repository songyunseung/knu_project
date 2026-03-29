# AI Server (Qwen3.5)

사용자 입력을 받아서  
의도와 서비스 정보를 JSON 형태로 반환하는 AI 서버

---

## 작동 방식

1. 사용자가 키오스크에서 문장을 입력하거나 말함  
2. backend가 해당 문장을 AI 서버로 전달  
3. AI 서버가 Qwen3.5 모델로 문장을 분석  
4. 분석 결과를 JSON 형태로 변환  
5. backend가 JSON을 받아서 화면 이동 또는 기능 실행

---

## 예시

입력:
주민등록등본 발급하고 싶어요

출력:
{
  "intent": "issue_document",
  "serviceId": "RESIDENT_REGISTRATION_COPY",
  "confidence": 0.95
}

---

## 특징

- 자연어를 그대로 쓰지 않고 JSON으로 변환해서 반환
- backend에서 바로 처리 가능
- 현재는 API 대신 로컬 모델(Qwen3.5)로 테스트 중