from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from fastapi.responses import FileResponse

from ..core.config import REPOSITORY_ROOT, get_settings
from ..core.research import (
    build_research_status,
    clear_research_job,
    run_research_job,
    start_research_job,
    update_research_job,
)
from ..schemas.research import (
    ClimateDatasetBuildRequest,
    ResearchJobResponse,
    ResearchStatusResponse,
    SatelliteDownloadRequest,
)

router = APIRouter(tags=["research"])


@router.get(
    "/api/v1/research/status",
    response_model=ResearchStatusResponse,
    summary="Retorna o status dos datasets e jobs de pesquisa.",
)
def research_status() -> ResearchStatusResponse:
    return ResearchStatusResponse.model_validate(build_research_status())


@router.post(
    "/api/v1/research/satellite-download",
    response_model=ResearchJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Inicia pesquisa/download Sentinel-2 em background.",
)
def start_satellite_download(
    payload: SatelliteDownloadRequest,
    background_tasks: BackgroundTasks,
) -> ResearchJobResponse:
    try:
        job = start_research_job(
            key="satellite-download",
            label="Download Sentinel-2",
            initial_message="Pesquisa STAC CDSE agendada.",
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    settings = get_settings()

    def task() -> str:
        from ..download_satellite_dataset import DownloadRunOptions, run_satellite_download

        def progress(message: str) -> None:
            update_research_job("satellite-download", message)

        summary = run_satellite_download(
            DownloadRunOptions(
                output_dir=settings.historical_eval_dir,
                env_file=REPOSITORY_ROOT / ".env",
                datetime_range=payload.datetime_range,
                max_items=payload.max_items,
                filename_timezone=payload.filename_timezone,
                overwrite=payload.overwrite,
                dry_run=payload.dry_run,
                progress_callback=progress,
            ),
        )
        if summary.dry_run:
            return f"Dry-run concluido: {summary.candidates} candidatos encontrados."
        return (
            f"Download concluido: {summary.downloaded} baixados, "
            f"{summary.skipped_existing} existentes, {summary.failed} falhas."
        )

    background_tasks.add_task(run_research_job, "satellite-download", task)
    return ResearchJobResponse.model_validate(job)


@router.delete(
    "/api/v1/research/jobs/{job_key}",
    response_model=ResearchStatusResponse,
    summary="Remove um job de pesquisa preso ou finalizado do status em memoria.",
)
def clear_research_job_status(job_key: str) -> ResearchStatusResponse:
    clear_research_job(job_key)
    return ResearchStatusResponse.model_validate(build_research_status())


@router.post(
    "/api/v1/research/climate-dataset",
    response_model=ResearchJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Inicia a montagem do CSV multimodal em background.",
)
def start_climate_dataset_build(
    payload: ClimateDatasetBuildRequest,
    background_tasks: BackgroundTasks,
) -> ResearchJobResponse:
    try:
        job = start_research_job(
            key="climate-dataset",
            label="Dataset multimodal",
            initial_message="Pipeline multimodal agendado.",
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    settings = get_settings()

    def task() -> str:
        from ..climate_pipeline import ClimatePipelineOptions, run_climate_pipeline

        def progress(message: str) -> None:
            update_research_job("climate-dataset", message)

        summary = run_climate_pipeline(
            ClimatePipelineOptions(
                input_dir=settings.historical_eval_dir,
                output_file=settings.climate_dataset_path,
                device=payload.device,
                api_timeout=payload.api_timeout,
                sleep_seconds=payload.sleep_seconds,
                max_images=payload.max_images,
                progress_callback=progress,
            ),
        )
        if summary.rows == 0 and summary.failed > 0:
            first_error = summary.errors[0] if summary.errors else "erro desconhecido"
            raise RuntimeError(f"CSV sem linhas: {first_error}")
        if summary.failed:
            first_error = summary.errors[0] if summary.errors else "erro desconhecido"
            return (
                f"CSV gerado: {summary.rows} linhas, {summary.failed} falhas "
                f"em {summary.attempted} imagens. Primeira falha: {first_error}"
            )
        return f"CSV gerado: {summary.rows} linhas, {summary.failed} falhas em {summary.attempted} imagens."

    background_tasks.add_task(run_research_job, "climate-dataset", task)
    return ResearchJobResponse.model_validate(job)


@router.get(
    "/api/v1/research/climate-dataset.csv",
    summary="Baixa o CSV multimodal gerado.",
)
def download_climate_dataset() -> FileResponse:
    dataset_path = get_settings().climate_dataset_path
    if not dataset_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="O CSV multimodal ainda nao foi gerado.",
        )

    return FileResponse(
        dataset_path,
        media_type="text/csv",
        filename=dataset_path.name,
    )
