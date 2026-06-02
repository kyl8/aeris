from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd


TEMPERATURE_COLUMN = "temperature_2m"
TIMESTAMP_COLUMN = "timestamp_weather"


@dataclass(frozen=True, slots=True)
class CoverageThresholds:
    monthly_min_ratio: float = 0.85
    annual_min_ratio: float = 0.85


def _ensure_datetime(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work[TIMESTAMP_COLUMN] = pd.to_datetime(work[TIMESTAMP_COLUMN], errors="coerce")
    return work.dropna(subset=[TIMESTAMP_COLUMN])


def normalize_weather_frame(df: pd.DataFrame) -> pd.DataFrame:
    work = _ensure_datetime(df)
    numeric_columns = [
        "latitude",
        "longitude",
        "temperature_2m",
        "relative_humidity_2m",
        "dew_point_2m",
        "precipitation",
        "rain",
        "snowfall",
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
    ]
    for column in numeric_columns:
        if column in work.columns:
            work[column] = pd.to_numeric(work[column], errors="coerce")
    if "city" not in work.columns:
        work["city"] = "regional"
    return work.sort_values(TIMESTAMP_COLUMN).reset_index(drop=True)


def aggregate_monthly(df: pd.DataFrame) -> pd.DataFrame:
    work = normalize_weather_frame(df)
    if work.empty:
        return pd.DataFrame()
    work["year"] = work[TIMESTAMP_COLUMN].dt.year
    work["month"] = work[TIMESTAMP_COLUMN].dt.month
    grouped = work.groupby(["city", "year", "month"], dropna=False)
    summary = grouped.agg(
        temperature_mean=("temperature_2m", "mean"),
        temperature_max=("temperature_2m", "max"),
        temperature_min=("temperature_2m", "min"),
        precipitation_sum=("precipitation", "sum"),
        humidity_mean=("relative_humidity_2m", "mean"),
        dew_point_mean=("dew_point_2m", "mean"),
        pressure_mean=("surface_pressure", "mean"),
        pressure_msl_mean=("pressure_msl", "mean"),
        cloud_cover_mean=("cloud_cover", "mean"),
        radiation_mean=("shortwave_radiation", "mean"),
        wind_speed_mean=("wind_speed_10m", "mean"),
        sample_count=("temperature_2m", "count"),
    ).reset_index()
    summary["period"] = summary["year"].astype(str) + "-" + summary["month"].astype(str).str.zfill(2)
    summary["expected_hour_count"] = summary.apply(
        lambda row: pd.Period(f"{int(row['year'])}-{int(row['month']):02d}", freq="M").days_in_month * 24,
        axis=1,
    )
    summary["coverage_ratio"] = summary["sample_count"] / summary["expected_hour_count"]
    return summary


def aggregate_annual(monthly: pd.DataFrame) -> pd.DataFrame:
    if monthly.empty:
        return pd.DataFrame()
    grouped = monthly.groupby(["city", "year"], dropna=False)
    summary = grouped.agg(
        temperature_mean=("temperature_mean", "mean"),
        temperature_max=("temperature_max", "max"),
        temperature_min=("temperature_min", "min"),
        precipitation_sum=("precipitation_sum", "sum"),
        humidity_mean=("humidity_mean", "mean"),
        dew_point_mean=("dew_point_mean", "mean"),
        pressure_mean=("pressure_mean", "mean"),
        pressure_msl_mean=("pressure_msl_mean", "mean"),
        cloud_cover_mean=("cloud_cover_mean", "mean"),
        radiation_mean=("radiation_mean", "mean"),
        wind_speed_mean=("wind_speed_mean", "mean"),
        sample_count=("sample_count", "sum"),
        expected_hour_count=("expected_hour_count", "sum"),
    ).reset_index()
    summary["coverage_ratio"] = summary["sample_count"] / summary["expected_hour_count"]
    return summary


def aggregate_regional(summary: pd.DataFrame, group_columns: Iterable[str]) -> pd.DataFrame:
    if summary.empty:
        return pd.DataFrame()
    groups = list(group_columns)
    grouped = summary.groupby(groups, dropna=False)
    regional = grouped.agg(
        temperature_mean=("temperature_mean", "mean"),
        temperature_max=("temperature_max", "mean"),
        temperature_min=("temperature_min", "mean"),
        precipitation_sum=("precipitation_sum", "mean"),
        humidity_mean=("humidity_mean", "mean"),
        dew_point_mean=("dew_point_mean", "mean"),
        pressure_mean=("pressure_mean", "mean"),
        cloud_cover_mean=("cloud_cover_mean", "mean"),
        radiation_mean=("radiation_mean", "mean"),
        wind_speed_mean=("wind_speed_mean", "mean"),
        sample_count=("sample_count", "sum"),
        expected_hour_count=("expected_hour_count", "sum"),
    ).reset_index()
    regional["city"] = "regional"
    regional["coverage_ratio"] = regional["sample_count"] / regional["expected_hour_count"]
    return regional


def compare_periods(annual_regional: pd.DataFrame, periods: list[tuple[str, int, int]]) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for label, start_year, end_year in periods:
        subset = annual_regional.loc[annual_regional["year"].between(start_year, end_year)]
        records.append(
            {
                "period": label,
                "start_year": start_year,
                "end_year": end_year,
                "years": int(subset["year"].nunique()) if not subset.empty else 0,
                "temperature_mean": float(subset["temperature_mean"].mean()) if not subset.empty else None,
                "temperature_max_mean": float(subset["temperature_max"].mean()) if not subset.empty else None,
                "temperature_min_mean": float(subset["temperature_min"].mean()) if not subset.empty else None,
                "precipitation_sum_mean": float(subset["precipitation_sum"].mean()) if not subset.empty else None,
                "coverage_ratio_mean": float(subset["coverage_ratio"].mean()) if not subset.empty else None,
            },
        )
    return pd.DataFrame(records)


def coverage_gaps(monthly: pd.DataFrame, threshold: float = 0.85) -> pd.DataFrame:
    if monthly.empty:
        return pd.DataFrame(columns=["city", "year", "month", "coverage_ratio", "sample_count", "expected_hour_count"])
    gaps = monthly.loc[monthly["coverage_ratio"] < threshold].copy()
    return gaps[["city", "year", "month", "coverage_ratio", "sample_count", "expected_hour_count"]]
