from __future__ import annotations

import csv
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Callable

from dotenv import dotenv_values

from .config import REPOSITORY_ROOT, get_settings


logger = logging.getLogger(__name__)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
CDSE_ENV_PATH = REPOSITORY_ROOT / ".env"


@dataclass(slots=True)
class ResearchJobSnapshot:
    key: str
    label: str
    status: str
    message: str
    started_at: datetime | None = None
    finished_at: datetime | None = None


_jobs_lock = Lock()
_jobs: dict[str, ResearchJobSnapshot] = {}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _snapshot_to_dict(job: ResearchJobSnapshot) -> dict[str, object]:
    return {
        "key": job.key,
        "label": job.label,
        "status": job.status,
        "message": job.message,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    }


def get_research_jobs() -> list[dict[str, object]]:
    with _jobs_lock:
        return [_snapshot_to_dict(job) for job in _jobs.values()]


def start_research_job(key: str, label: str, initial_message: str) -> dict[str, object]:
    with _jobs_lock:
        current_job = _jobs.get(key)
        if current_job is not None and current_job.status == "running":
            raise RuntimeError(f"O job '{label}' ja esta em execucao.")

        job = ResearchJobSnapshot(
            key=key,
            label=label,
            status="running",
            message=initial_message,
            started_at=_now_utc(),
            finished_at=None,
        )
        _jobs[key] = job
        return _snapshot_to_dict(job)


def update_research_job(key: str, message: str) -> None:
    with _jobs_lock:
        job = _jobs.get(key)
        if job is not None and job.status == "running":
            job.message = message


def finish_research_job(key: str, status: str, message: str) -> None:
    with _jobs_lock:
        job = _jobs.get(key)
        if job is None:
            return

        job.status = status
        job.message = message
        job.finished_at = _now_utc()


def clear_research_job(key: str) -> None:
    with _jobs_lock:
        _jobs.pop(key, None)


def run_research_job(key: str, callback: Callable[[], str]) -> None:
    try:
        message = callback()
    except Exception as exc:
        logger.exception("research_job_failed", extra={"job_key": key})
        finish_research_job(key, "failed", str(exc))
        return

    finish_research_job(key, "succeeded", message)


def iter_historical_images(directory: Path | None = None) -> list[Path]:
    settings = get_settings()
    base_dir = directory or settings.historical_eval_dir
    if not base_dir.exists():
        return []

    return sorted(
        path
        for path in base_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def count_csv_rows(csv_path: Path | None = None) -> int:
    settings = get_settings()
    target_path = csv_path or settings.climate_dataset_path
    if not target_path.exists():
        return 0

    with target_path.open("r", encoding="utf-8", newline="") as file_handle:
        reader = csv.reader(file_handle)
        row_count = sum(1 for _ in reader)

    return max(row_count - 1, 0)


def cdse_credentials_configured(env_path: Path = CDSE_ENV_PATH) -> bool:
    env_values = dotenv_values(env_path) if env_path.exists() else {}
    username = os.getenv("CDSE_USERNAME") or env_values.get("CDSE_USERNAME")
    password = os.getenv("CDSE_PASSWORD") or env_values.get("CDSE_PASSWORD")
    return bool(username and password)


def build_research_status() -> dict[str, object]:
    settings = get_settings()
    images = iter_historical_images(settings.historical_eval_dir)
    latest_image = max(images, key=lambda path: path.stat().st_mtime, default=None)
    dataset_path = settings.climate_dataset_path
    baixada_report_path = REPOSITORY_ROOT / "outputs" / "baixada_santista" / "report.html"
    baixada_report_updated_at = (
        datetime.fromtimestamp(baixada_report_path.stat().st_mtime, tz=timezone.utc)
        if baixada_report_path.exists()
        else None
    )

    return {
        "historical_eval_dir": str(settings.historical_eval_dir),
        "image_count": len(images),
        "latest_image": latest_image.name if latest_image is not None else None,
        "climate_dataset_path": str(dataset_path),
        "climate_dataset_exists": dataset_path.exists(),
        "climate_dataset_rows": count_csv_rows(dataset_path),
        "baixada_report_path": str(baixada_report_path),
        "baixada_report_exists": baixada_report_path.exists(),
        "baixada_report_updated_at": baixada_report_updated_at,
        "cdse_credentials_configured": cdse_credentials_configured(),
        "jobs": get_research_jobs(),
    }
