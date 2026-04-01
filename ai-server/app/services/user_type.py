from typing import Dict, Any

from app.config import settings
from app.model import model_instance
from app.prompts import USER_TYPE_SYSTEM_PROMPT
from app.exceptions import ModelResponseError


ALLOWED_USER_TYPES = {
    "ELDERLY",
    "WHEELCHAIR",
    "VISUAL_IMPAIRMENT",
    "HEARING_IMPAIRMENT",
    "NORMAL",
    "UNKNOWN",
}


def classify_user_type(text: str) -> Dict[str, Any]:
    try:
        result = model_instance.generate_json(USER_TYPE_SYSTEM_PROMPT, text)
        parsed = result["parsed"]

        user_type = parsed.get("userType", "UNKNOWN")
        if user_type not in ALLOWED_USER_TYPES:
            user_type = "UNKNOWN"

        confidence = parsed.get("confidence", 0.0)
        try:
            confidence = float(confidence)
        except Exception:
            confidence = 0.0

        confidence = max(0.0, min(1.0, confidence))

        if confidence < settings.USER_TYPE_CONFIDENCE_THRESHOLD:
            user_type = "UNKNOWN"

        reason = parsed.get("reason", "분류 근거를 찾지 못했습니다.")
        if not isinstance(reason, str):
            reason = "분류 근거를 찾지 못했습니다."

        return {
            "task": "classify_user_type",
            "success": True,
            "fallback_used": False,
            "userType": user_type,
            "confidence": confidence,
            "reason": reason,
            "raw_text": result["raw_text"],
            "model_name": result["model_name"],
        }

    except ModelResponseError as e:
        return {
            "task": "classify_user_type",
            "success": False,
            "fallback_used": True,
            "userType": "UNKNOWN",
            "confidence": 0.0,
            "reason": f"모델 응답 처리 실패: {str(e)}",
            "raw_text": "",
            "model_name": model_instance.model_id,
        }