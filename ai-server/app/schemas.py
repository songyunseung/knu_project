from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


UserType = Literal[
    "ELDERLY",
    "WHEELCHAIR",
    "VISUAL_IMPAIRMENT",
    "HEARING_IMPAIRMENT",
    "NORMAL",
    "UNKNOWN",
]

IntentType = Literal[
    "issue_document",
    "submit_application",
    "pay_or_check",
    "welfare_service",
    "general_question",
    "unknown",
]

ServiceIdType = Literal[
    "RESIDENT_REGISTRATION_COPY",
    "FAMILY_CERTIFICATE",
    "MOVE_IN_REPORT",
    "HEALTH_INSURANCE",
    "MARRIAGE_CERTIFICATE",
    "TAX_CERTIFICATE",
    "UNKNOWN",
]


class HealthResponse(BaseModel):
    status: str
    model: str


class BaseTextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=300, description="사용자 입력 문장")
    session_id: Optional[str] = Field(default=None, description="세션 ID")
    locale: str = Field(default="ko-KR", description="언어 코드")

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("text must not be empty.")
        return v


class UserTypeResponse(BaseModel):
    task: Literal["classify_user_type"]
    success: bool
    fallback_used: bool
    userType: UserType
    confidence: float
    reason: str
    raw_text: str
    model_name: str


class ServiceRecommendResponse(BaseModel):
    task: Literal["recommend_service"]
    success: bool
    fallback_used: bool
    intent: IntentType
    serviceId: ServiceIdType
    confidence: float
    answer: str
    raw_text: str
    model_name: str