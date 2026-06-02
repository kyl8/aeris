from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PredictionRequest(BaseModel):
    image_base64: str | None = Field(
        default=None,
        description="Imagem em base64 ou data URL. Útil para chamadas sem multipart.",
    )
    image_name: str | None = Field(default=None, description="Nome opcional da imagem.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "image_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
                "image_name": "satellite.png",
            }
        }
    )


class PredictionResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "class": "cloudy/overcast",
                    "confidence": 0.92,
                    "heatmap": "iVBORw0KGgoAAAANSUhEUgAA...",
                    "model_name": "aeris-weather-siglip2",
                    "model_version": "0.1.0",
                    "source": "transformers",
                    "created_at": "2026-04-30T12:00:00Z",
                    "inference_ms": 18.4,
                }
            ]
        },
    )

    prediction_class: str = Field(alias="class", description="Classe climática prevista.")
    confidence: float = Field(ge=0, le=1, description="Confiança da predição.")
    heatmap: str | None = Field(default=None, description="Heatmap opcional em base64.")
    model_name: str = Field(description="Nome do artefato ou modelo utilizado.")
    model_version: str = Field(description="Versão do modelo.")
    source: str = Field(description="Origem da predição: transformers, pytorch, onnx ou heuristic.")
    created_at: datetime = Field(description="Momento em que a predição foi registrada.")
    inference_ms: float = Field(ge=0, description="Latência da inferência em milissegundos.")
    top_predictions: list[dict[str, float | str]] = Field(
        default_factory=list,
        description="Ranking das classes mais prováveis com confiança normalizada.",
    )
    image_profile: dict[str, float] = Field(
        default_factory=dict,
        description="Perfil visual extraído da imagem para auditoria e explicabilidade.",
    )
    explanation: list[str] = Field(
        default_factory=list,
        description="Observações legíveis sobre os sinais usados pela inferência.",
    )
    risk_flags: list[str] = Field(
        default_factory=list,
        description="Alertas de confiabilidade, fallback ou qualidade do frame.",
    )


class PredictionHistoryItem(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "class": "rain/storm",
                    "confidence": 0.84,
                    "heatmap": "iVBORw0KGgoAAAANSUhEUgAA...",
                    "model_name": "aeris-weather-siglip2",
                    "model_version": "0.1.0",
                    "source": "transformers",
                    "created_at": "2026-04-30T12:00:00Z",
                    "image_name": "satellite.png",
                    "inference_ms": 21.1,
                }
            ]
        },
    )

    id: int
    prediction_class: str = Field(alias="class")
    confidence: float = Field(ge=0, le=1)
    heatmap: str | None = None
    model_name: str
    model_version: str
    source: str
    created_at: datetime
    image_name: str | None = None
    inference_ms: float


class PredictionHistoryResponse(BaseModel):
    items: list[PredictionHistoryItem]
    total: int


class ErrorResponse(BaseModel):
    error: str
    code: int


class HealthResponse(BaseModel):
    status: Literal["online"]
