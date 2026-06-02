from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from aeris.config import AerisPaths
from aeris.core.cache import CacheManager
from aeris.core.retry import RetryConfig
from aeris.core.sqlite import MetadataStore
from aeris.logging import RunLogger, configure_logging, get_logger

from .aggregation import aggregate_annual, aggregate_monthly, aggregate_regional, compare_periods, coverage_gaps
from .anomalies import annual_anomalies, compute_anomalies, compute_monthly_baseline, detect_outliers, top_anomaly_years
from .openmeteo_client import (
    DEFAULT_DAILY_VARIABLES,
    DEFAULT_HOURLY_VARIABLES,
    OpenMeteoClient,
    OpenMeteoRequest,
    iter_year_chunks,
    write_csv_chunk,
)
from .plots import generate_all_plots
from .regions import BAIXADA_SANTISTA, Region
from .report import write_reports
from .trend import detect_period_dependency, linear_trend, trends_by_city


def _today_utc() -> date:
    return datetime.now(timezone.utc).date()


@dataclass(frozen=True, slots=True)
class BaixadaSantistaAnalysisConfig:
    dataset_root: Path = Path("datasets")
    output_root: Path = Path("outputs")
    start_date: date = date(1940, 1, 1)
    end_date: date = _today_utc()
    baseline_start_year: int = 1961
    baseline_end_year: int = 1990
    source_model: str = "era5"
    timezone: str = "America/Sao_Paulo"
    years_per_chunk: int = 1
    use_grid: bool = False
    grid_spacing_degrees: float = 0.25
    force_download: bool = False
    force_rebuild_outputs: bool = False
    json_logs: bool = False
    log_level: str = "INFO"
    max_batches: int | None = None
    request_delay_seconds: float = 1.0
    retry_attempts: int = 8
    retry_base_delay_seconds: float = 5.0
    retry_max_delay_seconds: float = 300.0
    hourly_variables: tuple[str, ...] = DEFAULT_HOURLY_VARIABLES
    daily_variables: tuple[str, ...] = DEFAULT_DAILY_VARIABLES


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, pd.DataFrame):
        return _json_safe(value.to_dict(orient="records"))
    if isinstance(value, pd.Series):
        return _json_safe(value.to_dict())
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return _json_safe(value.item())
        except Exception:
            pass
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def _write_dataframe(df: pd.DataFrame, csv_path: Path, parquet_path: Path, logger: RunLogger) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False, encoding="utf-8")
    try:
        df.to_parquet(parquet_path, index=False)
    except Exception as exc:
        logger.warn("parquet_write_failed", path=str(parquet_path), error=str(exc))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_safe(payload), ensure_ascii=False, indent=2), encoding="utf-8")


def _records(df: pd.DataFrame, limit: int | None = None) -> list[dict[str, Any]]:
    if df.empty:
        return []
    output = df.copy()
    if limit is not None:
        output = output.head(limit)
    output = output.where(pd.notna(output), None)
    return _json_safe(output.to_dict(orient="records"))


def _coordinate_signature(region: Region) -> list[dict[str, Any]]:
    return [
        {
            "name": coordinate.name,
            "latitude": round(coordinate.latitude, 6),
            "longitude": round(coordinate.longitude, 6),
        }
        for coordinate in region.coordinates
    ]


def _build_timeseries_manifest(
    *,
    config: BaixadaSantistaAnalysisConfig,
    region: Region,
    hourly_rows: int,
    complete: bool,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "region_slug": region.slug,
        "region_bbox": list(region.bbox),
        "coordinates": _coordinate_signature(region),
        "start_date": config.start_date.isoformat(),
        "end_date": config.end_date.isoformat(),
        "baseline_start_year": config.baseline_start_year,
        "baseline_end_year": config.baseline_end_year,
        "source_model": config.source_model,
        "timezone": config.timezone,
        "hourly_variables": list(config.hourly_variables),
        "daily_variables": list(config.daily_variables),
        "complete": complete,
        "hourly_rows": hourly_rows,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }


def _manifest_matches_request(
    manifest: dict[str, Any],
    *,
    config: BaixadaSantistaAnalysisConfig,
    region: Region,
) -> tuple[bool, str]:
    if not manifest.get("complete"):
        return False, "manifest_marks_timeseries_as_incomplete"
    if manifest.get("region_slug") != region.slug:
        return False, "region_slug_mismatch"
    if manifest.get("coordinates") != _coordinate_signature(region):
        return False, "coordinate_grid_mismatch"
    if manifest.get("source_model") != config.source_model:
        return False, "source_model_mismatch"
    if manifest.get("timezone") != config.timezone:
        return False, "timezone_mismatch"
    if tuple(manifest.get("hourly_variables", [])) != tuple(config.hourly_variables):
        return False, "hourly_variables_mismatch"
    if tuple(manifest.get("daily_variables", [])) != tuple(config.daily_variables):
        return False, "daily_variables_mismatch"

    try:
        existing_start = date.fromisoformat(str(manifest["start_date"]))
        existing_end = date.fromisoformat(str(manifest["end_date"]))
    except Exception:
        return False, "invalid_manifest_dates"

    if existing_start > config.start_date or existing_end < config.end_date:
        return False, f"period_not_covered existing={existing_start.isoformat()}..{existing_end.isoformat()}"
    return True, "usable"


def _existing_timeseries_is_usable(
    *,
    manifest_path: Path,
    config: BaixadaSantistaAnalysisConfig,
    region: Region,
    logger: RunLogger,
) -> bool:
    if not manifest_path.exists():
        logger.warn(
            "existing_timeseries_manifest_missing",
            path=str(manifest_path),
            action="rebuild_timeseries",
        )
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warn(
            "existing_timeseries_manifest_unreadable",
            path=str(manifest_path),
            error=str(exc),
            action="rebuild_timeseries",
        )
        return False
    matches, reason = _manifest_matches_request(manifest, config=config, region=region)
    if not matches:
        logger.warn(
            "existing_timeseries_ignored",
            reason=reason,
            path=str(manifest_path),
            action="rebuild_timeseries",
        )
        return False
    logger.info(
        "existing_timeseries_manifest_valid",
        start_date=manifest.get("start_date"),
        end_date=manifest.get("end_date"),
        hourly_rows=manifest.get("hourly_rows"),
    )
    return True


def _combine_monthly_parts(parts: list[pd.DataFrame]) -> pd.DataFrame:
    non_empty = [part for part in parts if not part.empty]
    if not non_empty:
        return pd.DataFrame()

    work = pd.concat(non_empty, ignore_index=True)
    group_columns = ["city", "year", "month"]
    mean_columns = [
        "temperature_mean",
        "humidity_mean",
        "dew_point_mean",
        "pressure_mean",
        "pressure_msl_mean",
        "cloud_cover_mean",
        "radiation_mean",
        "wind_speed_mean",
    ]
    for column in mean_columns:
        if column in work.columns:
            work[column] = pd.to_numeric(work[column], errors="coerce")
            work[f"_{column}_weighted"] = work[column] * pd.to_numeric(work["sample_count"], errors="coerce")

    aggregation: dict[str, tuple[str, str]] = {
        "temperature_max": ("temperature_max", "max"),
        "temperature_min": ("temperature_min", "min"),
        "precipitation_sum": ("precipitation_sum", "sum"),
        "sample_count": ("sample_count", "sum"),
        "expected_hour_count": ("expected_hour_count", "max"),
        "period": ("period", "first"),
    }
    for column in mean_columns:
        weighted_column = f"_{column}_weighted"
        if weighted_column in work.columns:
            aggregation[weighted_column] = (weighted_column, "sum")

    grouped = work.groupby(group_columns, dropna=False).agg(**aggregation).reset_index()
    grouped["sample_count"] = pd.to_numeric(grouped["sample_count"], errors="coerce")
    for column in mean_columns:
        weighted_column = f"_{column}_weighted"
        if weighted_column in grouped.columns:
            grouped[column] = grouped[weighted_column] / grouped["sample_count"].replace(0, pd.NA)
            grouped = grouped.drop(columns=[weighted_column])
    grouped["coverage_ratio"] = grouped["sample_count"] / grouped["expected_hour_count"].replace(0, pd.NA)
    return grouped.sort_values(group_columns).reset_index(drop=True)


def _load_existing_monthly_summary(
    *,
    timeseries_csv: Path,
    config: BaixadaSantistaAnalysisConfig,
    logger: RunLogger,
    chunksize: int = 250_000,
) -> tuple[pd.DataFrame, int]:
    start_timestamp = pd.Timestamp(config.start_date)
    end_timestamp = pd.Timestamp(config.end_date + timedelta(days=1))
    monthly_parts: list[pd.DataFrame] = []
    total_rows = 0
    filtered_rows = 0

    for chunk_index, chunk in enumerate(pd.read_csv(timeseries_csv, chunksize=chunksize), start=1):
        total_rows += len(chunk)
        if "timestamp_weather" not in chunk.columns:
            raise RuntimeError(f"{timeseries_csv} does not contain timestamp_weather")
        chunk["timestamp_weather"] = pd.to_datetime(chunk["timestamp_weather"], errors="coerce")
        chunk = chunk.loc[(chunk["timestamp_weather"] >= start_timestamp) & (chunk["timestamp_weather"] < end_timestamp)]
        if chunk.empty:
            continue
        filtered_rows += len(chunk)
        monthly_parts.append(aggregate_monthly(chunk))
        logger.debug(
            "existing_timeseries_chunk_loaded",
            chunk=chunk_index,
            rows=len(chunk),
            filtered_rows=filtered_rows,
        )

    monthly = _combine_monthly_parts(monthly_parts)
    logger.info(
        "existing_timeseries_loaded",
        path=str(timeseries_csv),
        rows_scanned=total_rows,
        rows_used=filtered_rows,
        monthly_rows=len(monthly),
    )
    return monthly, filtered_rows


def _select_region(config: BaixadaSantistaAnalysisConfig) -> Region:
    if config.use_grid:
        return BAIXADA_SANTISTA.with_grid(config.grid_spacing_degrees)
    return BAIXADA_SANTISTA


def _load_or_fetch_hourly(
    *,
    config: BaixadaSantistaAnalysisConfig,
    region: Region,
    paths: AerisPaths,
    store: MetadataStore,
    output_dir: Path,
    logger: RunLogger,
) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    timeseries_csv = output_dir / "climate_timeseries.csv"
    timeseries_parquet = output_dir / "climate_timeseries.parquet"
    manifest_path = output_dir / "climate_timeseries_manifest.json"

    if timeseries_csv.exists() and not config.force_rebuild_outputs and not config.force_download:
        if _existing_timeseries_is_usable(
            manifest_path=manifest_path,
            config=config,
            region=region,
            logger=logger,
        ):
            logger.info("using_existing_timeseries", path=str(timeseries_csv))
            monthly, rows_used = _load_existing_monthly_summary(
                timeseries_csv=timeseries_csv,
                config=config,
                logger=logger,
            )
            return pd.DataFrame(), monthly, rows_used

    if timeseries_csv.exists():
        logger.warn("replacing_timeseries_file", path=str(timeseries_csv))
        timeseries_csv.unlink()
    if timeseries_parquet.exists():
        timeseries_parquet.unlink()
    if manifest_path.exists():
        manifest_path.unlink()

    cache = CacheManager(paths.cache)
    client = OpenMeteoClient(
        cache=cache,
        retry_config=RetryConfig(
            attempts=config.retry_attempts,
            base_delay_seconds=config.retry_base_delay_seconds,
            max_delay_seconds=config.retry_max_delay_seconds,
        ),
        min_interval_seconds=config.request_delay_seconds,
        logger=logger.child(source=config.source_model, period=f"{config.start_date.year}-{config.end_date.year}"),
    )
    monthly_parts: list[pd.DataFrame] = []
    hourly_rows = 0
    failures = 0
    completed_batches = 0
    parquet_writer = None
    parquet_schema = None
    parquet_available = False
    try:
        import pyarrow as pa  # type: ignore
        import pyarrow.parquet as pq  # type: ignore

        parquet_available = True
    except Exception as exc:
        pa = None  # type: ignore
        pq = None  # type: ignore
        logger.warn("parquet_streaming_unavailable", error=str(exc))

    chunks = list(iter_year_chunks(config.start_date, config.end_date, years_per_chunk=config.years_per_chunk))
    total_batches = len(region.coordinates) * len(chunks)
    batch_index = 0
    stop_requested = False
    for coordinate in region.coordinates:
        for chunk_start, chunk_end in chunks:
            batch_index += 1
            if config.max_batches is not None and batch_index > config.max_batches:
                logger.warn("max_batches_reached", max_batches=config.max_batches)
                stop_requested = True
                break
            logger.progress(
                "fetching_weather_batch",
                current=batch_index,
                total=total_batches,
                city=coordinate.name,
                source=config.source_model,
                start_date=chunk_start,
                end_date=chunk_end,
            )
            request = OpenMeteoRequest(
                coordinate=coordinate,
                start_date=chunk_start,
                end_date=chunk_end,
                hourly_variables=config.hourly_variables,
                daily_variables=config.daily_variables,
                timezone=config.timezone,
                source_model=config.source_model,
            )
            try:
                chunk = client.fetch_hourly_dataframe(request, force=config.force_download)
            except Exception as exc:
                failures += 1
                payload = {
                    "region": region.slug,
                    "city": coordinate.name,
                    "latitude": coordinate.latitude,
                    "longitude": coordinate.longitude,
                    "start_date": chunk_start.isoformat(),
                    "end_date": chunk_end.isoformat(),
                    "source_model": config.source_model,
                }
                store.add_retry_task("openmeteo_weather_batch", payload, error=str(exc))
                logger.error(
                    "weather_batch_download_failed",
                    batch=batch_index,
                    city=coordinate.name,
                    start_date=chunk_start,
                    end_date=chunk_end,
                    error=str(exc),
                    retry_queue="openmeteo_weather_batch",
                )
                continue

            try:
                write_csv_chunk(timeseries_csv, chunk)
                if parquet_available and pa is not None and pq is not None:
                    table = pa.Table.from_pandas(chunk, preserve_index=False)
                    table = table.replace_schema_metadata(None)
                    if parquet_schema is None:
                        parquet_schema = table.schema
                    else:
                        table = table.cast(parquet_schema, safe=False)
                    if parquet_writer is None:
                        parquet_writer = pq.ParquetWriter(timeseries_parquet, parquet_schema)
                    parquet_writer.write_table(table)
                monthly_parts.append(aggregate_monthly(chunk))
                hourly_rows += len(chunk)
                completed_batches += 1
                logger.info("weather_batch_processed", batch=batch_index, rows=len(chunk), total_rows=hourly_rows)
            except Exception as exc:
                failures += 1
                store.add_retry_task(
                    "openmeteo_weather_batch_write",
                    {
                        "region": region.slug,
                        "batch": batch_index,
                        "source_model": config.source_model,
                    },
                    error=str(exc),
                )
                logger.error("weather_batch_write_failed", batch=batch_index, error=str(exc))
        if stop_requested:
            break

    if failures:
        logger.warn("weather_fetch_completed_with_failures", failures=failures, completed_batches=completed_batches)
    if not monthly_parts:
        raise RuntimeError("No weather data was fetched. Check network, Open-Meteo parameters and cache.")

    if parquet_writer is not None:
        parquet_writer.close()
    manifest = _build_timeseries_manifest(
        config=config,
        region=region,
        hourly_rows=hourly_rows,
        complete=config.max_batches is None and failures == 0,
    )
    _write_json(manifest_path, manifest)
    hourly = pd.DataFrame()
    monthly = _combine_monthly_parts(monthly_parts)
    return hourly, monthly, hourly_rows


def run_baixada_santista_analysis(config: BaixadaSantistaAnalysisConfig | None = None) -> dict[str, Any]:
    config = config or BaixadaSantistaAnalysisConfig()
    configure_logging(config.log_level, json_format=config.json_logs)

    paths = AerisPaths.from_root(config.dataset_root).ensure()
    store = MetadataStore(paths.metadata_db)
    region = _select_region(config)
    output_dir = config.output_root / region.slug
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "plots").mkdir(parents=True, exist_ok=True)
    period = f"{config.start_date.year}-{config.end_date.year}"
    logger = RunLogger(
        get_logger("analysis.baixada_santista"),
        region=region.slug,
        period=period,
        source=config.source_model,
    )
    logger.info(
        "analysis_started",
        coordinates=len(region.coordinates),
        baseline=f"{config.baseline_start_year}-{config.baseline_end_year}",
        output_dir=str(output_dir),
    )

    hourly, monthly_city, hourly_rows = _load_or_fetch_hourly(
        config=config,
        region=region,
        paths=paths,
        store=store,
        output_dir=output_dir,
        logger=logger,
    )

    monthly_regional = aggregate_regional(monthly_city, ["year", "month"])
    monthly_summary = pd.concat([monthly_city, monthly_regional], ignore_index=True)
    annual_city = aggregate_annual(monthly_city)
    annual_regional = aggregate_regional(annual_city, ["year"])
    annual_summary = pd.concat([annual_city, annual_regional], ignore_index=True)

    baseline = compute_monthly_baseline(
        monthly_summary,
        baseline_start_year=config.baseline_start_year,
        baseline_end_year=config.baseline_end_year,
    )
    monthly_anomaly_summary = compute_anomalies(monthly_summary, baseline)
    annual_anomaly_summary = annual_anomalies(monthly_anomaly_summary)

    regional_annual = annual_summary.loc[annual_summary["city"] == "regional"].copy()
    trend_result = linear_trend(regional_annual, value_column="temperature_mean")
    city_trend_df = trends_by_city(annual_city, value_column="temperature_mean")
    period_dependency_df = detect_period_dependency(
        regional_annual,
        [
            ("1940-1969", 1940, 1969),
            ("1970-1999", 1970, 1999),
            (f"2000-{config.end_date.year}", 2000, config.end_date.year),
            ("baseline_1961-1990", 1961, 1990),
            (f"recent_1991-{config.end_date.year}", 1991, config.end_date.year),
        ],
    )
    period_comparison_df = compare_periods(
        regional_annual,
        [
            ("1940-1969", 1940, 1969),
            ("1970-1999", 1970, 1999),
            (f"2000-{config.end_date.year}", 2000, config.end_date.year),
            ("baseline_1961-1990", 1961, 1990),
            (f"recent_1991-{config.end_date.year}", 1991, config.end_date.year),
        ],
    )
    monthly_gaps = coverage_gaps(monthly_summary)
    outliers = detect_outliers(monthly_anomaly_summary, annual_anomaly_summary)
    if not annual_anomaly_summary.empty and "city" in annual_anomaly_summary.columns:
        regional_anomaly_years = annual_anomaly_summary.loc[annual_anomaly_summary["city"] == "regional"]
    else:
        regional_anomaly_years = pd.DataFrame()
    warm_years, cold_years = top_anomaly_years(regional_anomaly_years, n=10)

    _write_dataframe(monthly_summary, output_dir / "monthly_summary.csv", output_dir / "monthly_summary.parquet", logger)
    _write_dataframe(annual_summary, output_dir / "annual_summary.csv", output_dir / "annual_summary.parquet", logger)
    _write_dataframe(monthly_anomaly_summary, output_dir / "monthly_anomalies.csv", output_dir / "monthly_anomalies.parquet", logger)
    _write_dataframe(annual_anomaly_summary, output_dir / "annual_anomalies.csv", output_dir / "annual_anomalies.parquet", logger)

    plots: dict[str, str] = {}
    try:
        plots = generate_all_plots(
            output_dir=output_dir / "plots",
            annual_regional=regional_annual,
            monthly_summary=monthly_summary,
            monthly_anomalies=monthly_anomaly_summary,
            city_trends=city_trend_df,
            trend=trend_result.to_dict(),
        )
    except Exception as exc:
        logger.warn("plot_generation_failed", error=str(exc))

    result: dict[str, Any] = {
        "region": {
            "slug": region.slug,
            "name": region.name,
            "bbox": region.bbox,
            "coordinates": [asdict(coordinate) for coordinate in region.coordinates],
        },
        "source_weather": config.source_model,
        "period": {
            "start_date": config.start_date.isoformat(),
            "end_date": config.end_date.isoformat(),
            "start_year": int(regional_annual["year"].min()) if not regional_annual.empty else None,
            "end_year": int(regional_annual["year"].max()) if not regional_annual.empty else None,
        },
        "baseline": {
            "start_year": config.baseline_start_year,
            "end_year": config.baseline_end_year,
        },
        "regional_trend": trend_result.to_dict(),
        "city_trends": _records(city_trend_df),
        "period_dependency": _records(period_dependency_df),
        "period_comparison": _records(period_comparison_df),
        "top_warm_years": _records(warm_years),
        "top_cold_years": _records(cold_years),
        "outliers": _json_safe(outliers),
        "coverage": {
            "hourly_rows": hourly_rows if hourly_rows else int(len(hourly)),
            "monthly_rows": int(len(monthly_summary)),
            "annual_rows": int(len(annual_summary)),
            "monthly_gap_count": int(len(monthly_gaps)),
            "monthly_gap_examples": _records(monthly_gaps, limit=50),
        },
        "plots": plots,
        "outputs": {
            "climate_timeseries_csv": str(output_dir / "climate_timeseries.csv"),
            "climate_timeseries_parquet": str(output_dir / "climate_timeseries.parquet"),
            "annual_summary_csv": str(output_dir / "annual_summary.csv"),
            "monthly_summary_csv": str(output_dir / "monthly_summary.csv"),
            "trend_analysis_json": str(output_dir / "trend_analysis.json"),
            "report_md": str(output_dir / "report.md"),
            "report_html": str(output_dir / "report.html"),
        },
        "metadata": {
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "method": "hourly_reanalysis_to_monthly_annual_linear_trend_with_baseline_anomalies",
            "notes": [
                "ERA5/Open-Meteo is used as weather reanalysis/tabular context, not as satellite imagery.",
                "Trend does not prove exclusive attribution to global warming.",
            ],
        },
    }
    _write_json(output_dir / "trend_analysis.json", result)
    markdown_path, html_path = write_reports(result, output_dir)
    result["outputs"]["report_md"] = str(markdown_path)
    result["outputs"]["report_html"] = str(html_path)

    store.record_event(
        run_id=None,
        module="analysis.baixada_santista",
        level="INFO",
        event="analysis_completed",
        payload={"regional_trend": trend_result.to_dict(), "outputs": result["outputs"]},
    )
    logger.info(
        "analysis_completed",
        slope_celsius_per_decade=trend_result.slope_per_decade,
        p_value=trend_result.p_value,
        confidence=trend_result.confidence,
        significant=trend_result.significant,
    )
    return _json_safe(result)
