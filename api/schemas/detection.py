from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    x: float = Field(ge=0, le=1, description="Coordenada X do canto superior esquerdo (fração 0-1).")
    y: float = Field(ge=0, le=1, description="Coordenada Y do canto superior esquerdo (fração 0-1).")
    width: float = Field(ge=0, le=1, description="Largura da caixa (fração 0-1).")
    height: float = Field(ge=0, le=1, description="Altura da caixa (fração 0-1).")


class DetectionItem(BaseModel):
    label: str = Field(description="Rótulo do objeto detectado.")
    confidence: float = Field(ge=0, le=1, description="Confiança da detecção.")
    box: BoundingBox = Field(description="Caixa delimitadora normalizada.")


class DetectionResponse(BaseModel):
    detections: list[DetectionItem] = Field(default_factory=list, description="Objetos detectados no frame.")
    model_name: str = Field(description="Modelo de detecção utilizado.")
    source: str = Field(description="Origem da detecção.")
    inference_ms: float = Field(ge=0, description="Latência da inferência em milissegundos.")
    width: int = Field(gt=0, description="Largura do frame analisado em pixels.")
    height: int = Field(gt=0, description="Altura do frame analisado em pixels.")
