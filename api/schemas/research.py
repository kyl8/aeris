from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ResearchJobState = Literal["running", "succeeded", "failed"]


class ResearchJobResponse(BaseModel):
    key: str
    label: str
    status: ResearchJobState
    message: str
    started_at: datetime | None = None
    finished_at: datetime | None = None


class ResearchStatusResponse(BaseModel):
    historical_eval_dir: str
    image_count: int
    latest_image: str | None
    climate_dataset_path: str
    climate_dataset_exists: bool
    climate_dataset_rows: int
    baixada_report_path: str
    baixada_report_exists: bool
    baixada_report_updated_at: datetime | None = None
    cdse_credentials_configured: bool
    jobs: list[ResearchJobResponse]


class SatelliteDownloadRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "dry_run": False,
                "max_items": None,
                "overwrite": False,
            }
        }
    )

    dry_run: bool = Field(default=False, description="Quando true, pesquisa STAC sem descarregar imagens.")
    max_items: int | None = Field(default=None, ge=1, description="Limite opcional de items STAC. None = pega tudo.")
    overwrite: bool = Field(default=False, description="Sobrescreve imagens existentes.")
    datetime_range: str = Field(
        default="2015-01-01T00:00:00Z/2026-05-17T23:59:59Z",
        description="Intervalo STAC no formato inicio/fim. Padrão: 2015 até hoje.",
    )
    filename_timezone: str = Field(default="America/Sao_Paulo", description="Timezone usada no nome do arquivo.")


class ClimateDatasetBuildRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "device": "auto",
                "max_images": 10,
            }
        }
    )

    device: Literal["auto", "cuda", "cpu"] = Field(default="auto", description="Dispositivo para inferência.")
    max_images: int | None = Field(default=None, ge=1, description="Limite opcional de imagens para teste.")
    sleep_seconds: float = Field(default=1.0, ge=0, description="Pausa entre chamadas Open-Meteo.")
    api_timeout: float = Field(default=30.0, gt=0, description="Timeout das chamadas Open-Meteo.")
