from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from aeris.config import AerisPaths
from aeris.core.sqlite import MetadataStore
from aeris.dataset.balancing import balance_dataset
from aeris.dataset.builder import ImageManifestRecord, MultimodalDatasetBuilder
from aeris.dataset.exports import export_dataset
from aeris.logging import RunLogger, configure_logging, get_logger
from aeris.satellite.base import SatelliteSearchQuery
from aeris.satellite.landsat import LandsatDownloader
from aeris.satellite.sentinel2 import Sentinel2Downloader


@dataclass(frozen=True, slots=True)
class AerisPipelineConfig:
    dataset_root: Path = Path("datasets")
    start_date: date = date(2015, 1, 1)
    end_date: date = date.today()
    bbox: tuple[float, float, float, float] = (-47.10, -24.40, -46.05, -23.78)
    max_cloud_cover: float | None = 80.0
    max_items_per_source: int | None = None
    include_sentinel2: bool = True
    include_landsat: bool = False
    overwrite_downloads: bool = False
    log_level: str = "INFO"
    json_logs: bool = False


class AerisPipeline:
    """High-level scalable Aeris data pipeline orchestrator."""

    def __init__(self, config: AerisPipelineConfig) -> None:
        configure_logging(config.log_level, json_format=config.json_logs)
        self.config = config
        self.paths = AerisPaths.from_root(config.dataset_root).ensure()
        self.store = MetadataStore(self.paths.metadata_db)
        self.logger = RunLogger(get_logger("pipeline.aeris"), region="baixada_santista")

    def download_satellite_imagery(self) -> list[Path]:
        query = SatelliteSearchQuery(
            bbox=self.config.bbox,
            start_date=self.config.start_date,
            end_date=self.config.end_date,
            max_cloud_cover=self.config.max_cloud_cover,
            limit=self.config.max_items_per_source,
        )
        downloaded: list[Path] = []
        downloaders = []
        if self.config.include_sentinel2:
            downloaders.append(Sentinel2Downloader(output_dir=self.paths.raw_sentinel2, thumbnail_dir=self.paths.thumbnails))
        if self.config.include_landsat:
            downloaders.append(LandsatDownloader(output_dir=self.paths.raw_landsat, thumbnail_dir=self.paths.thumbnails))

        for downloader in downloaders:
            items = downloader.search(query)
            for item in items:
                if item.cloud_cover is not None and self.config.max_cloud_cover is not None and item.cloud_cover > self.config.max_cloud_cover:
                    self.logger.warn(
                        "satellite_item_skipped",
                        source=item.source,
                        item_id=item.item_id,
                        cloud_cover=item.cloud_cover,
                        reason="cloud_threshold",
                    )
                    continue
                result = downloader.download(item, overwrite=self.config.overwrite_downloads)
                self.store.upsert_download(
                    download_id=result.item_id,
                    source=result.source,
                    status=result.status,
                    local_path=str(result.local_path) if result.local_path else None,
                    checksum=result.checksum,
                    metadata=result.metadata,
                )
                if result.local_path is not None and result.status in {"downloaded", "cached"}:
                    downloaded.append(result.local_path)
        self.logger.summary("satellite_download_stage_completed", files=len(downloaded))
        return downloaded

    def build_dataset(
        self,
        image_manifest: list[ImageManifestRecord],
        weather_df: pd.DataFrame,
        *,
        source_weather: str = "era5",
    ) -> tuple[pd.DataFrame, dict[str, str]]:
        builder = MultimodalDatasetBuilder(paths=self.paths, store=self.store, logger=self.logger.child(module="dataset.builder"))
        samples = builder.build_samples(image_manifest, weather_df, source_weather=source_weather)
        records = [sample.to_record() for sample in samples]
        dataframe = pd.DataFrame(records)
        balanced, balance_metadata = balance_dataset(dataframe)
        self.logger.info(
            "dataset_balancing_completed",
            samples=len(dataframe),
            balanced_samples=len(balanced),
            imbalanced_classes=",".join(balance_metadata.get("imbalanced_classes", [])),
        )
        outputs = export_dataset(records, self.paths.exports)
        return balanced, outputs
