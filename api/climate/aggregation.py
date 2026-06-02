from __future__ import annotations

import logging

import pandas as pd

from .loader import TIMESTAMP_COLUMN


LOGGER = logging.getLogger("aeris.climate.aggregation")

AGGREGATION_COLUMNS = [
    "period",
    "temperature_mean",
    "temperature_min",
    "temperature_max",
    "temperature_std",
    "humidity_mean",
    "dew_point_mean",
    "precipitation_sum",
    "cloud_cover_mean",
    "shortwave_radiation_mean",
    "direct_radiation_mean",
    "diffuse_radiation_mean",
    "wind_speed_mean",
    "sample_count",
]

FREQUENCY_ALIASES = {
    "H": "h",
    "D": "D",
    "M": "MS",
    "Y": "YS",
}


def _empty_aggregation() -> pd.DataFrame:
    return pd.DataFrame(columns=AGGREGATION_COLUMNS)


def _format_period(timestamp: pd.Timestamp, freq: str) -> str:
    if freq == "H":
        return timestamp.strftime("%Y-%m-%dT%H:00")
    if freq == "D":
        return timestamp.strftime("%Y-%m-%d")
    if freq == "M":
        return timestamp.strftime("%Y-%m")
    if freq == "Y":
        return timestamp.strftime("%Y")
    return timestamp.isoformat()


def _ensure_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    normalized = df.copy()
    for column in columns:
        if column not in normalized.columns:
            normalized[column] = pd.NA
    return normalized


def aggregate_temperature(df: pd.DataFrame, freq: str = "M") -> pd.DataFrame:
    """Aggregate climate variables by hour, day, month or year."""

    normalized_freq = freq.upper()
    if normalized_freq not in FREQUENCY_ALIASES:
        raise ValueError("Frequencia invalida. Use H, D, M ou Y.")

    if df.empty:
        return _empty_aggregation()

    needed_columns = [
        "temperature_2m",
        "relative_humidity_2m",
        "dew_point_2m",
        "precipitation",
        "cloud_cover",
        "shortwave_radiation",
        "direct_radiation",
        "diffuse_radiation",
        "wind_speed_10m",
    ]
    work_df = _ensure_columns(df, needed_columns)
    work_df = work_df.set_index(TIMESTAMP_COLUMN)

    grouped = work_df.resample(FREQUENCY_ALIASES[normalized_freq])
    aggregation = grouped.agg(
        temperature_mean=("temperature_2m", "mean"),
        temperature_min=("temperature_2m", "min"),
        temperature_max=("temperature_2m", "max"),
        temperature_std=("temperature_2m", "std"),
        humidity_mean=("relative_humidity_2m", "mean"),
        dew_point_mean=("dew_point_2m", "mean"),
        precipitation_sum=("precipitation", "sum"),
        cloud_cover_mean=("cloud_cover", "mean"),
        shortwave_radiation_mean=("shortwave_radiation", "mean"),
        direct_radiation_mean=("direct_radiation", "mean"),
        diffuse_radiation_mean=("diffuse_radiation", "mean"),
        wind_speed_mean=("wind_speed_10m", "mean"),
        sample_count=("temperature_2m", "count"),
    )
    aggregation = aggregation.loc[aggregation["sample_count"] > 0].reset_index()
    aggregation["period"] = aggregation[TIMESTAMP_COLUMN].map(lambda value: _format_period(value, normalized_freq))
    aggregation = aggregation.drop(columns=[TIMESTAMP_COLUMN])
    aggregation = aggregation[AGGREGATION_COLUMNS]
    aggregation["temperature_std"] = aggregation["temperature_std"].fillna(0.0)

    LOGGER.info("[CLIMATE] Aggregated %d rows at freq=%s", len(aggregation), normalized_freq)
    return aggregation
