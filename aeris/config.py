from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AerisPaths:
    """Filesystem layout for large Aeris datasets.

    The layout intentionally separates real satellite imagery from weather
    reanalysis and labels. ERA5/Open-Meteo data is never treated as an image
    source.
    """

    root: Path

    @classmethod
    def from_root(cls, root: str | Path) -> "AerisPaths":
        return cls(root=Path(root).expanduser().resolve())

    @classmethod
    def default(cls) -> "AerisPaths":
        return cls.from_root(Path.cwd() / "datasets")

    @property
    def raw(self) -> Path:
        return self.root / "raw"

    @property
    def raw_sentinel2(self) -> Path:
        return self.raw / "sentinel2"

    @property
    def raw_landsat(self) -> Path:
        return self.raw / "landsat"

    @property
    def raw_weather(self) -> Path:
        return self.raw / "weather"

    @property
    def raw_metadata(self) -> Path:
        return self.raw / "metadata"

    @property
    def processed(self) -> Path:
        return self.root / "processed"

    @property
    def processed_images(self) -> Path:
        return self.processed / "images"

    @property
    def thumbnails(self) -> Path:
        return self.processed / "thumbnails"

    @property
    def tiles(self) -> Path:
        return self.processed / "tiles"

    @property
    def normalized(self) -> Path:
        return self.processed / "normalized"

    @property
    def augmented(self) -> Path:
        return self.processed / "augmented"

    @property
    def labels(self) -> Path:
        return self.root / "labels"

    @property
    def labels_automatic(self) -> Path:
        return self.labels / "automatic"

    @property
    def labels_manual(self) -> Path:
        return self.labels / "manual"

    @property
    def labels_verified(self) -> Path:
        return self.labels / "verified"

    @property
    def parquet(self) -> Path:
        return self.root / "parquet"

    @property
    def cache(self) -> Path:
        return self.root / "cache"

    @property
    def exports(self) -> Path:
        return self.root / "exports"

    @property
    def metadata_db(self) -> Path:
        return self.raw_metadata / "aeris_metadata.sqlite3"

    def directories(self) -> tuple[Path, ...]:
        return (
            self.raw_sentinel2,
            self.raw_landsat,
            self.raw_weather,
            self.raw_metadata,
            self.processed_images,
            self.thumbnails,
            self.tiles,
            self.normalized,
            self.augmented,
            self.labels_automatic,
            self.labels_manual,
            self.labels_verified,
            self.parquet,
            self.cache,
            self.exports,
        )

    def ensure(self) -> "AerisPaths":
        for directory in self.directories():
            directory.mkdir(parents=True, exist_ok=True)
        return self


DEFAULT_CLIMATE_CLASSES = (
    "clear",
    "cloudy",
    "overcast",
    "rain",
    "storm",
    "fog",
    "mist",
    "snow",
    "frost",
    "hail",
    "sandstorm",
    "smoke",
    "haze",
    "rainbow",
    "lightning",
)
