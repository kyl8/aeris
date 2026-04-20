from pydantic import BaseModel, ConfigDict, Field


class PredictionRequest(BaseModel):
    features: list[float] = Field(
        ...,
        min_length=1,
        description="Lista de valores numéricos usados na inferência.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "features": [12.5, 18.2, 9.1],
            }
        }
    )


class PredictionResponse(BaseModel):
    model_name: str
    model_version: str
    artifact_path: str | None
    feature_count: int
    prediction: float
    normalized_features: list[float]
    detail: str