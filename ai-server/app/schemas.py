from typing import Literal, Optional
from pydantic import BaseModel, Field


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
    text: str = Field(..., description="사용자 입력 문장")
    session_id: Optional[str] = Field(default=None, description="세션 ID")
    locale: str = Field(default="ko-KR", description="언어 코드")


class UserTypeResponse(BaseModel):
    task: Literal["classify_user_type"]
    userType: UserType
    confidence: float
    reason: str
    raw_text: str
    model_name: str


class ServiceRecommendResponse(BaseModel):
    task: Literal["recommend_service"]
    intent: IntentType
    serviceId: ServiceIdType
    confidence: float
    answer: str
    raw_text: str
    model_name: str