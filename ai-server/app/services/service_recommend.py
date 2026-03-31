from typing import Dict, Any

from app.model import model_instance
from app.prompts import SERVICE_RECOMMEND_SYSTEM_PROMPT


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


def recommend_service(text: str) -> Dict[str, Any]:
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

    answer = parsed.get("answer", "적절한 서비스를 찾지 못했습니다.")
    if not isinstance(answer, str):
        answer = "적절한 서비스를 찾지 못했습니다."

    return {
        "task": "recommend_service",
        "intent": intent,
        "serviceId": service_id,
        "confidence": confidence,
        "answer": answer,
        "raw_text": result["raw_text"],
        "model_name": result["model_name"],
    }