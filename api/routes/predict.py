from datetime import datetime, timezone

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from ..core.inference import get_predictor
from ..core.preprocessing import decode_base64_image
from ..core.storage import PredictionRecord, get_history_store
from ..schemas.prediction import ErrorResponse, PredictionResponse

router = APIRouter(tags=["prediction"])


@router.post(
    "/api/v1/predict",
    response_model=PredictionResponse,
    summary="Executa uma predição de imagem",
    responses={
        400: {"model": ErrorResponse, "description": "Entrada inválida."},
        422: {"model": ErrorResponse, "description": "Campos obrigatórios ausentes ou inválidos."},
    },
)
@router.post("/api/predict", include_in_schema=False)
async def predict(
    image: UploadFile | None = File(default=None, description="Imagem enviada como multipart/form-data."),
    image_base64: str | None = Form(default=None, description="Imagem codificada em base64 ou data URL."),
    persist: bool = Form(default=True, description="Quando false, executa inferência sem gravar no histórico."),
) -> PredictionResponse:
    if image is None and not image_base64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Envie um arquivo de imagem ou um payload base64.",
        )

    if image is not None:
        image_bytes = await image.read()
        image_name = image.filename
    else:
        try:
            image_bytes = decode_base64_image(image_base64 or "")
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        image_name = None

    if not image_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A imagem enviada está vazia.")

    predictor = get_predictor()

    try:
        outcome = predictor.predict(image_bytes=image_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    created_at = datetime.now(timezone.utc)
    if persist:
        record = PredictionRecord(
            id=None,
            created_at=created_at,
            climate_class=outcome.prediction_class,
            confidence=outcome.confidence,
            heatmap=outcome.heatmap,
            model_name=outcome.model_name,
            model_version=outcome.model_version,
            source=outcome.source,
            inference_ms=outcome.inference_ms,
            image_name=image_name,
        )

        stored_record = get_history_store().save(record)
        created_at = stored_record.created_at

    return PredictionResponse(
        prediction_class=outcome.prediction_class,
        confidence=outcome.confidence,
        heatmap=outcome.heatmap,
        model_name=outcome.model_name,
        model_version=outcome.model_version,
        source=outcome.source,
        created_at=created_at,
        inference_ms=outcome.inference_ms,
        top_predictions=outcome.top_predictions,
        image_profile=outcome.image_profile,
        explanation=outcome.explanation,
        risk_flags=outcome.risk_flags,
    )
