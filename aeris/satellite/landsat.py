from __future__ import annotations

from pathlib import Path

from aeris.logging import RunLogger, get_logger

from .stac import STACSatelliteDownloader


class LandsatDownloader(STACSatelliteDownloader):
    """Landsat Collection 2 Level-2 adapter for historical expansion.

    Landsat is used to expand the visual record back to 1972. This adapter
    searches public STAC metadata and downloads preview/visual assets when
    available. Full spectral COG processing can be added behind the same
    interface with rasterio/stackstac when the project needs band-level
    reprojection at scale.
    """

    source = "landsat"
    endpoint = "https://planetarycomputer.microsoft.com/api/stac/v1"
    collections = ("landsat-c2-l2",)
    asset_priority = ("rendered_preview", "thumbnail", "qa", "red", "green", "blue")

    def __init__(self, *, output_dir: Path, thumbnail_dir: Path, logger: RunLogger | None = None) -> None:
        super().__init__(
            output_dir=output_dir,
            thumbnail_dir=thumbnail_dir,
            logger=logger or RunLogger(get_logger("satellite.landsat"), source=self.source),
        )
