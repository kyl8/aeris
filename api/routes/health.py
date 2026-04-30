from fastapi import APIRouter

from ..schemas.prediction import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/api/v1/health", response_model=HealthResponse, summary="Verifica se a API está ativa")
@router.get("/health", response_model=HealthResponse, include_in_schema=False)
def health() -> HealthResponse:
    return HealthResponse(status="online")