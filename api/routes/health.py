from fastapi import APIRouter
from pydantic import BaseModel

from ..core.config import APP_NAME, APP_VERSION

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    docs: str


@router.get("/health", response_model=HealthResponse, summary="Verifica se a API está ativa")
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=APP_NAME,
        version=APP_VERSION,
        docs="/docs",
    )