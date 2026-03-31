# AI Server

사용자 입력을 받아서  
서비스 추천이나 사용자 유형을 JSON 형태로 반환하는 AI 서버

---

## 현재 방식

현재는 OpenAI API를 사용해서 동작하도록 구현함

처음에는 API 키가 없어서 원격 GPU 서버에서 로컬 모델(Qwen3.5-9B)로 테스트했지만,  
이제는 OpenAI API 기반으로 전환한 상태

---

## 작동 방식

1. 사용자가 키오스크에서 문장을 입력하거나 말함  
2. backend가 해당 문장을 AI 서버로 전달  
3. AI 서버가 OpenAI API로 문장을 분석  
4. 분석 결과를 JSON 형태로 변환  
5. backend가 JSON을 받아서 화면 이동 또는 기능 실행

---

## ⚙️ 실행 방법

### 1. 패키지 설치

프로젝트 루트에서 필요한 패키지를 설치

```bash
pip install -r requirements.txt
```

### 2. OpenAI API 키 설정
```bash
$env:OPENAI_API_KEY="여기에_API키"
```

### 3. 서버 실행

FastAPI 서버 실행
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 주요 기능

### 1. 사용자 유형 분석

- endpoint: `/classify/user-type`
- 입력 문장을 바탕으로 사용자 유형 분류
- 예: 시각 불편, 휠체어 사용 여부 등

예시 입력:
```json
{
  "text": "나 눈이 좀 안 좋아"
}

