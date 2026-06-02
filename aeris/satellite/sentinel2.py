from __future__ import annotations

from pathlib import Path

from aeris.logging import RunLogger, get_logger

from .stac import STACSatelliteDownloader


class Sentinel2Downloader(STACSatelliteDownloader):
    """Sentinel-2 L2A search/download adapter.

    Sentinel-2 is the main modern visual source for Aeris. Its valid period
    starts in 2015 and continues to the present.
    """

    source = "sentinel2"
    endpoint = "https://stac.dataspace.copernicus.eu/v1/"
    collections = ("sentinel-2-l2a",)
    asset_priority = ("visual", "thumbnail", "overview", "tci", "TCI", "true_color", "true-color")

    def __init__(self, *, output_dir: Path, thumbnail_dir: Path, logger: RunLogger | None = None) -> None:
        super().__init__(
            output_dir=output_dir,
            thumbnail_dir=thumbnail_dir,
            logger=logger or RunLogger(get_logger("satellite.sentinel2"), source=self.source),
        )
