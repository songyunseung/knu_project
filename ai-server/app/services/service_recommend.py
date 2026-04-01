from typing import Dict, Any

from app.config import settings
from app.model import model_instance
from app.prompts import SERVICE_RECOMMEND_SYSTEM_PROMPT
from app.exceptions import ModelResponseError


ALLOWED_INTENTS = {
    "issue_document",
    "submit_application",
    "pay_or_check",
    "welfare_service",
    "general_question",
    "unknown",
}

ALLOWED_SERVICE_IDS = {
    "RESIDENT_REGISTRATION_COPY",
    "FAMILY_CERTIFICATE",
    "MOVE_IN_REPORT",
    "HEALTH_INSURANCE",
    "MARRIAGE_CERTIFICATE",
    "TAX_CERTIFICATE",
    "UNKNOWN",
}


def _normalize_text(text: str) -> str:
    return text.strip().lower()


def _rule_based_service_match(text: str) -> Dict[str, Any] | None:
    t = _normalize_text(text)
    print("[DEBUG] normalized text:", t)

    # 주민등록등본
    if any(keyword in t for keyword in ["주민등록등본", "등본", "등본 발급", "초본"]):
        print("[DEBUG] rule matched: RESIDENT_REGISTRATION_COPY")
        return {
            "task": "recommend_service",
            "success": True,
            "fallback_used": False,
            "intent": "issue_document",
            "serviceId": "RESIDENT_REGISTRATION_COPY",
            "confidence": 0.99,
            "answer": "주민등록등본 발급 메뉴로 안내할게요.",
            "raw_text": '{"intent":"issue_document","serviceId":"RESIDENT_REGISTRATION_COPY","confidence":0.99,"answer":"주민등록등본 발급 메뉴로 안내할게요."}',
            "model_name": "rule_based",
        }

    # 가족관계증명서
    if "가족관계증명서" in t:
        print("[DEBUG] rule matched: FAMILY_CERTIFICATE")
        return {
            "task": "recommend_service",
            "success": True,
            "fallback_used": False,
            "intent": "issue_document",
            "serviceId": "FAMILY_CERTIFICATE",
            "confidence": 0.99,
            "answer": "가족관계증명서 발급 메뉴로 안내할게요.",
            "raw_text": '{"intent":"issue_document","serviceId":"FAMILY_CERTIFICATE","confidence":0.99,"answer":"가족관계증명서 발급 메뉴로 안내할게요."}',
            "model_name": "rule_based",
        }

    # 전입신고
    if any(keyword in t for keyword in ["전입신고", "이사 와서 신고", "주소 이전", "주소이전"]):
        print("[DEBUG] rule matched: MOVE_IN_REPORT")
        return {
            "task": "recommend_service",
            "success": True,
            "fallback_used": False,
            "intent": "submit_application",
            "serviceId": "MOVE_IN_REPORT",
            "confidence": 0.99,
            "answer": "전입신고 메뉴로 안내할게요.",
            "raw_text": '{"intent":"submit_application","serviceId":"MOVE_IN_REPORT","confidence":0.99,"answer":"전입신고 메뉴로 안내할게요."}',
            "model_name": "rule_based",
        }

    # 건강보험
    if any(keyword in t for keyword in ["건강보험", "건강보험료", "보험료 확인서"]):
        print("[DEBUG] rule matched: HEALTH_INSURANCE")
        return {
            "task": "recommend_service",
            "success": True,
            "fallback_used": False,
            "intent": "pay_or_check",
            "serviceId": "HEALTH_INSURANCE",
            "confidence": 0.99,
            "answer": "건강보험 관련 메뉴로 안내할게요.",
            "raw_text": '{"intent":"pay_or_check","serviceId":"HEALTH_INSURANCE","confidence":0.99,"answer":"건강보험 관련 메뉴로 안내할게요."}',
            "model_name": "rule_based",
        }

    # 혼인관계증명서
    if "혼인관계증명서" in t:
        print("[DEBUG] rule matched: MARRIAGE_CERTIFICATE")
        return {
            "task": "recommend_service",
            "success": True,
            "fallback_used": False,
            "intent": "issue_document",
            "serviceId": "MARRIAGE_CERTIFICATE",
            "confidence": 0.99,
            "answer": "혼인관계증명서 발급 메뉴로 안내할게요.",
            "raw_text": '{"intent":"issue_document","serviceId":"MARRIAGE_CERTIFICATE","confidence":0.99,"answer":"혼인관계증명서 발급 메뉴로 안내할게요."}',
            "model_name": "rule_based",
        }

    # 세금
    if any(keyword in t for keyword in ["세금", "납세", "세금 납부 확인서", "납세 확인서"]):
        print("[DEBUG] rule matched: TAX_CERTIFICATE")
        return {
            "task": "recommend_service",
            "success": True,
            "fallback_used": False,
            "intent": "pay_or_check",
            "serviceId": "TAX_CERTIFICATE",
            "confidence": 0.99,
            "answer": "세금 납부 확인 메뉴로 안내할게요.",
            "raw_text": '{"intent":"pay_or_check","serviceId":"TAX_CERTIFICATE","confidence":0.99,"answer":"세금 납부 확인 메뉴로 안내할게요."}',
            "model_name": "rule_based",
        }

    return None


def recommend_service(text: str) -> Dict[str, Any]:
    print("[DEBUG] recommend_service called with:", text)

    # 1. 규칙 기반 먼저 처리
    rule_result = _rule_based_service_match(text)
    if rule_result is not None:
        print("[DEBUG] returning rule-based result")
        return rule_result

    # 2. 규칙에 안 걸리면 LLM 사용
    print("[DEBUG] falling back to LLM")

    try:
        result = model_instance.generate_json(SERVICE_RECOMMEND_SYSTEM_PROMPT, text)
        parsed = result["parsed"]

        intent = parsed.get("intent", "unknown")
        if intent not in ALLOWED_INTENTS:
            intent = "unknown"

        service_id = parsed.get("serviceId", "UNKNOWN")
        if service_id not in ALLOWED_SERVICE_IDS:
            service_id = "UNKNOWN"

        confidence = parsed.get("confidence", 0.0)
        try:
            confidence = float(confidence)
        except Exception:
            confidence = 0.0

        confidence = max(0.0, min(1.0, confidence))

        if confidence < settings.SERVICE_CONFIDENCE_THRESHOLD:
            intent = "unknown"
            service_id = "UNKNOWN"

        answer = parsed.get("answer", "적절한 서비스를 찾지 못했습니다.")
        if not isinstance(answer, str):
            answer = "적절한 서비스를 찾지 못했습니다."

        return {
            "task": "recommend_service",
            "success": True,
            "fallback_used": False,
            "intent": intent,
            "serviceId": service_id,
            "confidence": confidence,
            "answer": answer,
            "raw_text": result["raw_text"],
            "model_name": result["model_name"],
        }

    except ModelResponseError as e:
        return {
            "task": "recommend_service",
            "success": False,
            "fallback_used": True,
            "intent": "unknown",
            "serviceId": "UNKNOWN",
            "confidence": 0.0,
            "answer": f"서비스 추천에 실패했습니다: {str(e)}",
            "raw_text": "",
            "model_name": model_instance.model_id,
        }