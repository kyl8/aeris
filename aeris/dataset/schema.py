from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class AerisSample:
    id: str
    image_path: str
    thumbnail_path: str | None
    source_image: str
    source_weather: str
    timestamp_image: str
    timestamp_weather: str
    latitude: float
    longitude: float
    country: str
    biome: str
    visual_label: str
    visual_confidence: float
    weather_label: str
    weather_confidence: float
    weather: dict[str, Any] = field(default_factory=dict)
    quality: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_record(self) -> dict[str, Any]:
        return asdict(self)

    def to_flat_record(self) -> dict[str, Any]:
        record = asdict(self)
        weather = record.pop("weather", {})
        quality = record.pop("quality", {})
        metadata = record.pop("metadata", {})
        for key, value in weather.items():
            record[f"weather.{key}"] = value
        for key, value in quality.items():
            record[f"quality.{key}"] = value
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                record[f"metadata.{key}"] = value
        return record
