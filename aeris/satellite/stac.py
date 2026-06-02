from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from aeris.core.integrity import file_sha256
from aeris.core.retry import RetryConfig, retry_sync
from aeris.logging import RunLogger

from .base import SatelliteDownloadResult, SatelliteItem, SatelliteSearchQuery
from .normalization import create_thumbnail


def _parse_datetime(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        timestamp = value
    else:
        try:
            timestamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return str(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class STACSatelliteDownloader:
    source: str
    endpoint: str
    collections: tuple[str, ...]
    asset_priority: tuple[str, ...]

    def __init__(
        self,
        *,
        output_dir: Path,
        thumbnail_dir: Path,
        logger: RunLogger,
        retry_config: RetryConfig | None = None,
        request_timeout: float = 60.0,
    ) -> None:
        self.output_dir = output_dir
        self.thumbnail_dir = thumbnail_dir
        self.logger = logger
        self.retry_config = retry_config or RetryConfig(attempts=3, base_delay_seconds=2.0)
        self.request_timeout = request_timeout

    def search(self, query: SatelliteSearchQuery) -> list[SatelliteItem]:
        try:
            from pystac_client import Client
        except Exception as exc:
            raise RuntimeError("pystac-client is required for satellite search") from exc

        catalog = Client.open(self.endpoint)
        stac_query: dict[str, Any] = {}
        if query.max_cloud_cover is not None:
            stac_query["eo:cloud_cover"] = {"lte": query.max_cloud_cover}
        search = catalog.search(
            collections=list(self.collections),
            bbox=list(query.bbox),
            datetime=query.datetime_interval,
            query=stac_query or None,
            limit=min(query.limit or 100, 100),
        )
        items: list[SatelliteItem] = []
        for index, item in enumerate(search.items(), start=1):
            if query.limit is not None and index > query.limit:
                break
            assets = {key: asset.href for key, asset in item.assets.items() if getattr(asset, "href", None)}
            properties = dict(item.properties)
            items.append(
                SatelliteItem(
                    item_id=item.id,
                    source=self.source,
                    timestamp=_parse_datetime(properties.get("datetime") or item.datetime),
                    bbox=tuple(item.bbox) if item.bbox else None,
                    cloud_cover=_coerce_float(properties.get("eo:cloud_cover")),
                    assets=assets,
                    metadata=properties,
                ),
            )
        self.logger.info("satellite_search_completed", source=self.source, items=len(items), collection=",".join(self.collections))
        return items

    def pick_asset(self, item: SatelliteItem) -> tuple[str, str] | None:
        lowered = {key.lower(): (key, href) for key, href in item.assets.items()}
        for preferred in self.asset_priority:
            match = lowered.get(preferred.lower())
            if match:
                return match
        for key, href in item.assets.items():
            searchable = f"{key} {href}".lower()
            if any(token in searchable for token in ("thumbnail", "preview", "visual", "true", "rendered")):
                return key, href
        return None

    def local_path_for(self, item: SatelliteItem, asset_key: str, href: str) -> Path:
        suffix = Path(urlparse(href).path).suffix
        if not suffix or len(suffix) > 8:
            suffix = ".bin"
        safe_id = "".join(char if char.isalnum() or char in "-_." else "_" for char in item.item_id)
        return self.output_dir / f"{safe_id}_{asset_key}{suffix}"

    def download(self, item: SatelliteItem, *, overwrite: bool = False) -> SatelliteDownloadResult:
        asset = self.pick_asset(item)
        if asset is None:
            return SatelliteDownloadResult(item_id=item.item_id, source=self.source, status="skipped", error="no_supported_asset")
        asset_key, href = asset
        output_path = self.local_path_for(item, asset_key, href)
        metadata_path = output_path.with_suffix(output_path.suffix + ".json")
        thumbnail_path = self.thumbnail_dir / f"{output_path.stem}.jpg"

        if output_path.exists() and not overwrite:
            checksum = file_sha256(output_path)
            self.logger.info("cache_hit", source=self.source, item_id=item.item_id, path=str(output_path))
            return SatelliteDownloadResult(
                item_id=item.item_id,
                source=self.source,
                status="cached",
                local_path=output_path,
                thumbnail_path=thumbnail_path if thumbnail_path.exists() else None,
                checksum=checksum,
                metadata=item.metadata,
            )

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.thumbnail_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info("cache_miss", source=self.source, item_id=item.item_id, asset=asset_key)

        def operation() -> None:
            response = requests.get(href, stream=True, timeout=self.request_timeout)
            response.raise_for_status()
            temp_path = output_path.with_suffix(output_path.suffix + ".part")
            with temp_path.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
            temp_path.replace(output_path)

        def on_retry(attempt: int, exc: BaseException, delay: float) -> None:
            self.logger.warn("download_retry", source=self.source, item_id=item.item_id, attempt=attempt, retry_delay_seconds=delay, error=str(exc))

        try:
            retry_sync(operation, config=self.retry_config, on_retry=on_retry)
            checksum = file_sha256(output_path)
            metadata_path.write_text(json.dumps(item.metadata, ensure_ascii=False, indent=2), encoding="utf-8")
            try:
                create_thumbnail(output_path, thumbnail_path)
            except Exception as exc:
                self.logger.warn("thumbnail_failed", source=self.source, item_id=item.item_id, error=str(exc))
            self.logger.info("download_completed", source=self.source, item_id=item.item_id, path=str(output_path))
            return SatelliteDownloadResult(
                item_id=item.item_id,
                source=self.source,
                status="downloaded",
                local_path=output_path,
                thumbnail_path=thumbnail_path if thumbnail_path.exists() else None,
                checksum=checksum,
                metadata=item.metadata,
            )
        except Exception as exc:
            self.logger.error("download_failed", source=self.source, item_id=item.item_id, error=str(exc))
            return SatelliteDownloadResult(item_id=item.item_id, source=self.source, status="failed", error=str(exc), metadata=item.metadata)


def _coerce_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
