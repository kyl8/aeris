from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pathlib import Path

from ..core.config import get_settings
from ..schemas.climate import ClimateAnalyzeRequest, ClimateAnalyzeResponse, ClimateBaixadaAnalysisRequest


router = APIRouter(tags=["climate"])


@router.post(
    "/api/v1/climate/analyze",
    response_model=ClimateAnalyzeResponse,
    summary="Analisa sinal local de aquecimento a partir do CSV multimodal.",
)
@router.post(
    "/climate/analyze",
    response_model=ClimateAnalyzeResponse,
    include_in_schema=False,
)
def analyze_climate(payload: ClimateAnalyzeRequest) -> ClimateAnalyzeResponse:
    from ..climate.pipeline import analyze_global_warming_signal

    csv_path = payload.csv_path or str(get_settings().climate_dataset_path)
    try:
        result = analyze_global_warming_signal(
            csv_path=csv_path,
            region_name=payload.region_name,
            image_path=payload.image_path,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return ClimateAnalyzeResponse(success=True, result=result)


@router.post(
    "/api/v1/climate/baixada-santista/analyze",
    response_model=ClimateAnalyzeResponse,
    summary="Executa analise historica Open-Meteo/ERA5 da Baixada Santista.",
)
def analyze_baixada_santista(payload: ClimateBaixadaAnalysisRequest) -> ClimateAnalyzeResponse:
    from datetime import datetime, timezone

    from aeris.climate.pipeline import BaixadaSantistaAnalysisConfig, run_baixada_santista_analysis

    try:
        result = run_baixada_santista_analysis(
            BaixadaSantistaAnalysisConfig(
                dataset_root=Path(payload.dataset_root),
                output_root=Path(payload.output_root),
                start_date=payload.start_date,
                end_date=payload.end_date or datetime.now(timezone.utc).date(),
                baseline_start_year=payload.baseline_start_year,
                baseline_end_year=payload.baseline_end_year,
                source_model=payload.source_model,
                years_per_chunk=payload.years_per_chunk,
                use_grid=payload.use_grid,
                grid_spacing_degrees=payload.grid_spacing_degrees,
                force_download=payload.force_download,
                force_rebuild_outputs=payload.force_rebuild_outputs,
                max_batches=payload.max_batches,
                request_delay_seconds=payload.request_delay_seconds,
                retry_attempts=payload.retry_attempts,
                retry_base_delay_seconds=payload.retry_base_delay_seconds,
                retry_max_delay_seconds=payload.retry_max_delay_seconds,
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return ClimateAnalyzeResponse(success=True, result=result)
