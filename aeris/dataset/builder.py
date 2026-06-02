from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from aeris.config import AerisPaths
from aeris.core.sqlite import MetadataStore
from aeris.logging import RunLogger, get_logger
from aeris.satellite.normalization import create_thumbnail

from .labels import infer_visual_label, infer_weather_label, quality_flags
from .schema import AerisSample


def stable_sample_id(source_image: str, image_path: str, timestamp_image: str, latitude: float, longitude: float) -> str:
    namespace = uuid.uuid5(uuid.NAMESPACE_DNS, "aeris.dataset.sample")
    raw = f"{source_image}|{image_path}|{timestamp_image}|{latitude:.6f}|{longitude:.6f}"
    return str(uuid.uuid5(namespace, raw))


def nearest_weather_row(weather_df: pd.DataFrame, timestamp: datetime, latitude: float, longitude: float) -> pd.Series:
    if weather_df.empty:
        raise ValueError("weather dataframe is empty")
    work = weather_df.copy()
    work["timestamp_weather"] = pd.to_datetime(work["timestamp_weather"], errors="coerce")
    work = work.dropna(subset=["timestamp_weather"])
    if work.empty:
        raise ValueError("weather dataframe has no valid timestamp_weather")
    work["time_delta_seconds"] = (work["timestamp_weather"] - pd.Timestamp(timestamp)).abs().dt.total_seconds()
    if "latitude" in work.columns and "longitude" in work.columns:
        work["space_delta"] = (work["latitude"].astype(float) - latitude).abs() + (work["longitude"].astype(float) - longitude).abs()
    else:
        work["space_delta"] = 0.0
    return work.sort_values(["time_delta_seconds", "space_delta"]).iloc[0]


@dataclass(slots=True)
class ImageManifestRecord:
    image_path: Path
    source_image: str
    timestamp_image: datetime
    latitude: float
    longitude: float
    country: str = "BR"
    biome: str = "mata_atlantica"
    metadata: dict[str, Any] | None = None


@dataclass(slots=True)
class MultimodalDatasetBuilder:
    paths: AerisPaths
    store: MetadataStore | None = None
    logger: RunLogger | None = None

    def __post_init__(self) -> None:
        self.paths.ensure()
        if self.store is None:
            self.store = MetadataStore(self.paths.metadata_db)
        if self.logger is None:
            self.logger = RunLogger(get_logger("dataset.builder"))

    def build_samples(
        self,
        image_manifest: Iterable[ImageManifestRecord],
        weather_df: pd.DataFrame,
        *,
        source_weather: str = "era5",
    ) -> list[AerisSample]:
        samples: list[AerisSample] = []
        manifest = list(image_manifest)
        total = len(manifest)
        for index, image_record in enumerate(manifest, start=1):
            assert self.logger is not None
            self.logger.progress("building_sample", current=index, total=total, image=str(image_record.image_path))
            try:
                weather_row = nearest_weather_row(
                    weather_df,
                    image_record.timestamp_image,
                    image_record.latitude,
                    image_record.longitude,
                )
                weather = {
                    key: _to_python(value)
                    for key, value in weather_row.to_dict().items()
                    if key
                    not in {
                        "city",
                        "latitude",
                        "longitude",
                        "country",
                        "biome",
                        "source_weather",
                        "requested_start_date",
                        "requested_end_date",
                        "time_delta_seconds",
                        "space_delta",
                    }
                }
                thumbnail_path = self.paths.thumbnails / f"{image_record.image_path.stem}.jpg"
                if not thumbnail_path.exists():
                    create_thumbnail(image_record.image_path, thumbnail_path)
                weather_label, weather_confidence = infer_weather_label(weather)
                visual_label, visual_confidence, image_stats = infer_visual_label(image_record.image_path, weather)
                sample = AerisSample(
                    id=stable_sample_id(
                        image_record.source_image,
                        str(image_record.image_path),
                        image_record.timestamp_image.isoformat(),
                        image_record.latitude,
                        image_record.longitude,
                    ),
                    image_path=str(image_record.image_path),
                    thumbnail_path=str(thumbnail_path) if thumbnail_path.exists() else None,
                    source_image=image_record.source_image,
                    source_weather=source_weather,
                    timestamp_image=image_record.timestamp_image.isoformat(),
                    timestamp_weather=str(weather.get("timestamp_weather")),
                    latitude=image_record.latitude,
                    longitude=image_record.longitude,
                    country=image_record.country,
                    biome=image_record.biome,
                    visual_label=visual_label,
                    visual_confidence=visual_confidence,
                    weather_label=weather_label,
                    weather_confidence=weather_confidence,
                    weather=weather,
                    quality=quality_flags(weather, image_stats),
                    metadata=image_record.metadata or {},
                )
                samples.append(sample)
                assert self.store is not None
                self.store.upsert_sample(sample.to_record())
            except Exception as exc:
                self.logger.error("sample_build_failed", image=str(image_record.image_path), error=str(exc))
                assert self.store is not None
                self.store.add_retry_task(
                    "sample_build",
                    {"image_path": str(image_record.image_path), "source_image": image_record.source_image},
                    error=str(exc),
                )
        self.logger.summary("dataset_build_completed", attempted=total, samples=len(samples), failed=total - len(samples))
        return samples


def _to_python(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    if pd.isna(value):
        return None
    return value
