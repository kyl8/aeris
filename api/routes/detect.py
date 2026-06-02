from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from ..core.detection import get_detector
from ..core.preprocessing import decode_base64_image
from ..schemas.detection import DetectionResponse
from ..schemas.prediction import ErrorResponse

router = APIRouter(tags=["detection"])


@router.post(
    "/api/v1/detect",
    response_model=DetectionResponse,
    summary="Detecta objetos climáticos no frame (sol, nuvens, chuva, etc.)",
    responses={
        400: {"model": ErrorResponse, "description": "Entrada inválida."},
        503: {"model": ErrorResponse, "description": "Modelo de detecção indisponível."},
    },
)
@router.post("/api/detect", include_in_schema=False)
async def detect(
    image: UploadFile | None = File(default=None, description="Imagem enviada como multipart/form-data."),
    image_base64: str | None = Form(default=None, description="Imagem codificada em base64 ou data URL."),
) -> DetectionResponse:
    if image is None and not image_base64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Envie um arquivo de imagem ou um payload base64.",
        )

    if image is not None:
        image_bytes = await image.read()
    else:
        try:
            image_bytes = decode_base64_image(image_base64 or "")
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not image_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A imagem enviada está vazia.")

    detector = get_detector()
    if not detector.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="O modelo de detecção OWL-ViT não está disponível.",
        )

    try:
        outcome = detector.detect(image_bytes=image_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return DetectionResponse(
        detections=[
            {"label": item.label, "confidence": item.confidence, "box": item.box}
            for item in outcome.detections
        ],
        model_name=outcome.model_name,
        source=outcome.source,
        inference_ms=outcome.inference_ms,
        width=outcome.width,
        height=outcome.height,
    )
