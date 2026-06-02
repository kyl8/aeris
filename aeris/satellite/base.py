from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class SatelliteSearchQuery:
    bbox: tuple[float, float, float, float]
    start_date: date
    end_date: date
    max_cloud_cover: float | None = 80.0
    limit: int | None = None

    @property
    def datetime_interval(self) -> str:
        return f"{self.start_date.isoformat()}T00:00:00Z/{self.end_date.isoformat()}T23:59:59Z"


@dataclass(frozen=True, slots=True)
class SatelliteItem:
    item_id: str
    source: str
    timestamp: str | None
    bbox: tuple[float, float, float, float] | None = None
    cloud_cover: float | None = None
    assets: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SatelliteDownloadResult:
    item_id: str
    source: str
    status: str
    local_path: Path | None = None
    thumbnail_path: Path | None = None
    checksum: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
