from fastapi import FastAPI
from app.model import model_instance
from app.schemas import (
    BaseTextRequest,
    HealthResponse,
    UserTypeResponse,
    ServiceRecommendResponse,
)
from app.services.user_type import classify_user_type
from app.services.service_recommend import recommend_service

app = FastAPI(
    title="Kiosk AI Server",
    version="1.0.0",
    description="관공서 키오스크용 AI/LLM 서버",
)


@app.on_event("startup")
def startup_event() -> None:
    model_instance.load()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", model=model_instance.model_id)


@app.post("/classify/user-type", response_model=UserTypeResponse)
def classify_user_type_endpoint(req: BaseTextRequest) -> UserTypeResponse:
    result = classify_user_type(req.text)
    return UserTypeResponse(**result)


@app.post("/classify/service", response_model=ServiceRecommendResponse)
def classify_service_endpoint(req: BaseTextRequest) -> ServiceRecommendResponse:
    result = recommend_service(req.text)
    return ServiceRecommendResponse(**result)