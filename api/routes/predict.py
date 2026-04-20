from fastapi import APIRouter, HTTPException, status

from ..core.inference import run_inference
from ..schemas.prediction import PredictionRequest, PredictionResponse

router = APIRouter(tags=["prediction"])


@router.post(
    "/predict",
    response_model=PredictionResponse,
    summary="Executa uma predição base",
)
def predict(payload: PredictionRequest) -> PredictionResponse:
    try:
        result = run_inference(payload.features)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return PredictionResponse(**result)