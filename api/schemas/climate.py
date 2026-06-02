from __future__ import annotations

from typing import Any
from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class ClimateAnalyzeRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "csv_path": "api/climate_multimodal_dataset.csv",
                "region_name": "Baixada Santista / Litoral SP",
                "image_path": "api/datasets/historical_eval/2023-07-15_10-12.jpg",
            },
        },
    )

    csv_path: str | None = Field(
        default=None,
        description="Caminho do CSV multimodal. Quando ausente, usa o CSV padrao do Aeris.",
    )
    region_name: str | None = Field(default=None, description="Nome humano da regiao analisada.")
    image_path: str | None = Field(default=None, description="Imagem opcional para contexto visual.")


class ClimateAnalyzeResponse(BaseModel):
    success: bool
    result: dict[str, Any]


class ClimateBaixadaAnalysisRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "dataset_root": "datasets",
                "output_root": "outputs",
                "start_date": "1940-01-01",
                "end_date": "2026-05-18",
                "source_model": "era5",
                "years_per_chunk": 1,
                "use_grid": False,
                "force_download": False,
                "force_rebuild_outputs": False,
                "max_batches": None,
                "request_delay_seconds": 1.0,
                "retry_attempts": 8,
            },
        },
    )

    dataset_root: str = Field(default="datasets", description="Raiz do data lake local do Aeris.")
    output_root: str = Field(default="outputs", description="Diretorio de saida dos relatorios e tabelas.")
    start_date: date = Field(default=date(1940, 1, 1), description="Inicio da serie historica.")
    end_date: date | None = Field(default=None, description="Fim da serie historica. Default: hoje.")
    baseline_start_year: int = Field(default=1961)
    baseline_end_year: int = Field(default=1990)
    source_model: str = Field(default="era5", description="Modelo Open-Meteo/ERA5, ex.: era5, era5_land ou best_match.")
    years_per_chunk: int = Field(default=1, ge=1, le=10)
    use_grid: bool = Field(default=False, description="Usa grid espacial em vez da lista de cidades.")
    grid_spacing_degrees: float = Field(default=0.25, gt=0)
    force_download: bool = Field(default=False)
    force_rebuild_outputs: bool = Field(default=False)
    max_batches: int | None = Field(default=None, ge=1, description="Limite para smoke tests sem baixar a serie inteira.")
    request_delay_seconds: float = Field(default=1.0, ge=0, le=60)
    retry_attempts: int = Field(default=8, ge=1, le=20)
    retry_base_delay_seconds: float = Field(default=5.0, ge=0, le=600)
    retry_max_delay_seconds: float = Field(default=300.0, ge=1, le=3600)
