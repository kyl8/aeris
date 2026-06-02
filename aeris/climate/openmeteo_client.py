from __future__ import annotations

import calendar
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterator

import pandas as pd
import requests

from aeris.core.cache import CacheManager
from aeris.core.retry import RetryConfig, retry_sync
from aeris.logging import RunLogger, get_logger

from .regions import Coordinate, Region


OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

DEFAULT_HOURLY_VARIABLES = (
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "precipitation",
    "rain",
    "snowfall",
    "weather_code",
    "pressure_msl",
    "surface_pressure",
    "cloud_cover",
    "cloud_cover_low",
    "cloud_cover_mid",
    "cloud_cover_high",
    "shortwave_radiation",
    "direct_radiation",
    "diffuse_radiation",
    "direct_normal_irradiance",
    "sunshine_duration",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "vapour_pressure_deficit",
)

DEFAULT_DAILY_VARIABLES = (
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "rain_sum",
    "snowfall_sum",
    "precipitation_hours",
    "shortwave_radiation_sum",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
)


@dataclass(frozen=True, slots=True)
class OpenMeteoRequest:
    coordinate: Coordinate
    start_date: date
    end_date: date
    hourly_variables: tuple[str, ...] = DEFAULT_HOURLY_VARIABLES
    daily_variables: tuple[str, ...] = DEFAULT_DAILY_VARIABLES
    timezone: str = "America/Sao_Paulo"
    source_model: str = "era5"
    cell_selection: str = "land"

    def cache_payload(self) -> dict[str, Any]:
        return {
            "latitude": round(self.coordinate.latitude, 6),
            "longitude": round(self.coordinate.longitude, 6),
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "hourly": self.hourly_variables,
            "daily": self.daily_variables,
            "timezone": self.timezone,
            "source_model": self.source_model,
            "cell_selection": self.cell_selection,
        }


@dataclass(slots=True)
class OpenMeteoClient:
    cache: CacheManager
    timeout_seconds: float = 60.0
    retry_config: RetryConfig = RetryConfig(attempts=8, base_delay_seconds=5.0, max_delay_seconds=300.0)
    min_interval_seconds: float = 0.0
    logger: RunLogger | None = None
    _last_request_at: float = field(default=0.0, init=False)

    def _logger(self) -> RunLogger:
        if self.logger is not None:
            return self.logger
        return RunLogger(get_logger("weather.openmeteo"))

    def _params(self, request: OpenMeteoRequest) -> dict[str, str]:
        params = {
            "latitude": str(request.coordinate.latitude),
            "longitude": str(request.coordinate.longitude),
            "start_date": request.start_date.isoformat(),
            "end_date": request.end_date.isoformat(),
            "hourly": ",".join(request.hourly_variables),
            "daily": ",".join(request.daily_variables),
            "timezone": request.timezone,
            "cell_selection": request.cell_selection,
        }
        if request.source_model and request.source_model != "best_match":
            params["models"] = request.source_model
        return params

    def _wait_for_rate_limit_window(self) -> None:
        if self.min_interval_seconds <= 0:
            return
        elapsed = time.monotonic() - self._last_request_at
        if 0 <= elapsed < self.min_interval_seconds:
            sleep_seconds = self.min_interval_seconds - elapsed
            self._logger().debug("request_throttled", sleep_seconds=round(sleep_seconds, 3))
            time.sleep(sleep_seconds)
        self._last_request_at = time.monotonic()

    def fetch_json(self, request: OpenMeteoRequest, *, force: bool = False) -> dict[str, Any]:
        cache_payload = request.cache_payload()
        logger = self._logger()
        cached = None if force else self.cache.load_json("openmeteo", cache_payload)
        if isinstance(cached, dict):
            logger.info(
                "cache_hit",
                city=request.coordinate.name,
                source=request.source_model,
                start_date=request.start_date,
                end_date=request.end_date,
            )
            return cached

        logger.info(
            "cache_miss",
            city=request.coordinate.name,
            source=request.source_model,
            start_date=request.start_date,
            end_date=request.end_date,
        )

        def operation() -> dict[str, Any]:
            self._wait_for_rate_limit_window()
            response = requests.get(OPEN_METEO_ARCHIVE_URL, params=self._params(request), timeout=self.timeout_seconds)
            try:
                response.raise_for_status()
            except requests.HTTPError as exc:
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        try:
                            setattr(exc, "retry_after_seconds", float(retry_after))
                        except ValueError:
                            pass
                raise
            payload = response.json()
            if isinstance(payload, dict) and payload.get("error"):
                raise RuntimeError(str(payload.get("reason") or payload))
            if not isinstance(payload, dict):
                raise RuntimeError("Open-Meteo returned a non-object payload")
            return payload

        def on_retry(attempt: int, exc: BaseException, delay: float) -> None:
            logger.warn(
                "retrying_download",
                city=request.coordinate.name,
                attempt=attempt,
                retry_delay_seconds=round(delay, 2),
                error=str(exc),
            )

        payload = retry_sync(operation, config=self.retry_config, on_retry=on_retry)
        self.cache.save_json("openmeteo", cache_payload, payload)
        logger.info(
            "download_completed",
            city=request.coordinate.name,
            source=request.source_model,
            start_date=request.start_date,
            end_date=request.end_date,
        )
        return payload

    def fetch_hourly_dataframe(self, request: OpenMeteoRequest, *, force: bool = False) -> pd.DataFrame:
        payload = self.fetch_json(request, force=force)
        hourly = payload.get("hourly")
        if not isinstance(hourly, dict) or not isinstance(hourly.get("time"), list):
            raise RuntimeError("Open-Meteo payload does not contain hourly.time")

        df = pd.DataFrame(hourly)
        df = df.rename(columns={"time": "timestamp_weather"})
        df["timestamp_weather"] = pd.to_datetime(df["timestamp_weather"], errors="coerce")
        df["city"] = request.coordinate.name
        df["latitude"] = request.coordinate.latitude
        df["longitude"] = request.coordinate.longitude
        df["country"] = request.coordinate.country
        df["biome"] = request.coordinate.biome
        df["source_weather"] = request.source_model
        df["requested_start_date"] = request.start_date.isoformat()
        df["requested_end_date"] = request.end_date.isoformat()
        for variable in request.hourly_variables:
            if variable not in df.columns:
                df[variable] = pd.NA
        return df


def iter_year_chunks(start_date: date, end_date: date, *, years_per_chunk: int = 1) -> Iterator[tuple[date, date]]:
    current = start_date
    while current <= end_date:
        target_year = min(end_date.year, current.year + years_per_chunk - 1)
        chunk_end = date(target_year, 12, 31)
        chunk_end = min(chunk_end, end_date)
        yield current, chunk_end
        current = chunk_end + timedelta(days=1)


def month_count_between(start_date: date, end_date: date) -> int:
    return (end_date.year - start_date.year) * 12 + end_date.month - start_date.month + 1


def expected_hour_count(start_date: date, end_date: date) -> int:
    days = (end_date - start_date).days + 1
    return days * 24


def fetch_region_hourly_iter(
    *,
    client: OpenMeteoClient,
    region: Region,
    start_date: date,
    end_date: date,
    hourly_variables: tuple[str, ...] = DEFAULT_HOURLY_VARIABLES,
    daily_variables: tuple[str, ...] = DEFAULT_DAILY_VARIABLES,
    timezone: str = "America/Sao_Paulo",
    source_model: str = "era5",
    years_per_chunk: int = 1,
    force: bool = False,
    max_batches: int | None = None,
) -> Iterator[pd.DataFrame]:
    chunks = list(iter_year_chunks(start_date, end_date, years_per_chunk=years_per_chunk))
    total = len(region.coordinates) * len(chunks)
    current = 0
    logger = client._logger()
    for coordinate in region.coordinates:
        for chunk_start, chunk_end in chunks:
            current += 1
            if max_batches is not None and current > max_batches:
                logger.warn("max_batches_reached", max_batches=max_batches)
                return
            logger.progress(
                "fetching_weather_batch",
                current=current,
                total=total,
                city=coordinate.name,
                source=source_model,
                start_date=chunk_start,
                end_date=chunk_end,
            )
            request = OpenMeteoRequest(
                coordinate=coordinate,
                start_date=chunk_start,
                end_date=chunk_end,
                hourly_variables=hourly_variables,
                daily_variables=daily_variables,
                timezone=timezone,
                source_model=source_model,
            )
            yield client.fetch_hourly_dataframe(request, force=force)


def write_csv_chunk(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, mode="a", index=False, header=not path.exists(), encoding="utf-8")


def days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]
