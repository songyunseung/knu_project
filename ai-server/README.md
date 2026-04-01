# Kiosk AI Server (ai-server)

관공서 키오스크를 위한 AI/LLM 서버입니다.
사용자의 자연어 입력(음성/텍스트)을 분석하여 **사용자 유형 분류** 및 **민원 서비스 추천**을 수행합니다.

---

## 1. 개요 (Overview)

이 서버는 키오스크 시스템에서 다음 역할을 담당합니다:

* 사용자 입력 분석 (텍스트 기반)
* 사용자 유형 분류 (노약자, 휠체어 등)
* 민원 서비스 추천
* JSON 형태의 구조화된 응답 반환

---

## 2. 아키텍처 (Architecture)

```text
[Frontend / Voice Input]
        ↓
    MCP Client
        ↓
     AI Server (this)
        ↓
   JSON Recommendation
        ↓
    MCP Client / Spring
        ↓
   UI 업데이트 (화면 이동, 접근성 적용)
```

---

## 3. 프로젝트 구조 (Project Structure)

```text
ai-server/
├─ app/
│  ├─ main.py                  # FastAPI 진입점
│  ├─ model.py                 # OpenAI 호출 및 JSON 파싱
│  ├─ prompts.py               # LLM 프롬프트 정의
│  ├─ schemas.py               # 요청/응답 스키마 (Pydantic)
│  ├─ config.py                # 환경설정 (모델, threshold 등)
│  ├─ exceptions.py            # 커스텀 예외
│  └─ services/
│     ├─ user_type.py          # 사용자 유형 분류 로직
│     └─ service_recommend.py  # 서비스 추천 로직
│
├─ requirements.txt
├─ run.sh
└─ README.md
```

---

## 4. 설치 및 실행 (Setup & Run)

### 1) Python 환경

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### 2) 패키지 설치

```bash
pip install -r requirements.txt
```

### 3) 환경변수 설정

```bash
export OPENAI_API_KEY=your_api_key
```

선택 옵션:

```bash
export OPENAI_MODEL=gpt-5-mini
export OPENAI_TIMEOUT=20
export OPENAI_MAX_OUTPUT_TOKENS=300
export USER_TYPE_CONFIDENCE_THRESHOLD=0.60
export SERVICE_CONFIDENCE_THRESHOLD=0.60
```

### 4) 서버 실행

```bash
uvicorn app.main:app --reload
```

또는

```bash
bash run.sh
```

---

## 5. API 명세 (API Endpoints)

---

### 5.1 Health Check

```http
GET /health
```

응답:

```json
{
  "status": "ok",
  "model": "gpt-5-mini"
}
```

---

### 5.2 사용자 유형 분류

```http
POST /classify/user-type
```

요청:

```json
{
  "text": "글씨가 잘 안 보여요"
}
```

응답:

```json
{
  "task": "classify_user_type",
  "success": true,
  "fallback_used": false,
  "userType": "VISUAL_IMPAIRMENT",
  "confidence": 0.92,
  "reason": "시력 불편을 직접 언급했다.",
  "raw_text": "{...}",
  "model_name": "gpt-5-mini"
}
```

---

### 5.3 서비스 추천

```http
POST /classify/service
```

요청:

```json
{
  "text": "주민등록등본 발급하고 싶어요"
}
```

응답:

```json
{
  "task": "recommend_service",
  "success": true,
  "fallback_used": false,
  "intent": "issue_document",
  "serviceId": "RESIDENT_REGISTRATION_COPY",
  "confidence": 0.95,
  "answer": "주민등록등본 발급 메뉴로 안내할게요.",
  "raw_text": "{...}",
  "model_name": "gpt-5-mini"
}
```

---

## 6. 사용자 유형 (User Types)

| 값                  | 설명      |
| ------------------ | ------- |
| ELDERLY            | 고령 사용자  |
| WHEELCHAIR         | 휠체어 사용자 |
| VISUAL_IMPAIRMENT  | 시각 장애   |
| HEARING_IMPAIRMENT | 청각 장애   |
| NORMAL             | 일반 사용자  |
| UNKNOWN            | 불확실     |

---

## 7. 서비스 ID (Service IDs)

| 값                          | 설명       |
| -------------------------- | -------- |
| RESIDENT_REGISTRATION_COPY | 주민등록등본   |
| FAMILY_CERTIFICATE         | 가족관계증명서  |
| MOVE_IN_REPORT             | 전입신고     |
| HEALTH_INSURANCE           | 건강보험 관련  |
| MARRIAGE_CERTIFICATE       | 혼인관계증명서  |
| TAX_CERTIFICATE            | 세금 납부 확인 |
| UNKNOWN                    | 불확실      |

---

## 8. Confidence 정책

| 범위          | 처리 방식      |
| ----------- | ---------- |
| ≥ 0.85      | 바로 추천      |
| 0.60 ~ 0.84 | 중간 신뢰도     |
| < 0.60      | UNKNOWN 처리 |

---

## 9. 에러 및 fallback 처리

다음 상황에서 fallback이 발생합니다:

* OpenAI API 실패
* JSON 파싱 실패
* 잘못된 응답 형식
* confidence threshold 미만

fallback 예시:

```json
{
  "success": false,
  "fallback_used": true,
  "userType": "UNKNOWN"
}
```

---

