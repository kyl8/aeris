from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from .loader import TEMPERATURE_COLUMN, TIMESTAMP_COLUMN


LOGGER = logging.getLogger("aeris.climate.trends")
SECONDS_PER_YEAR = 365.2425 * 24 * 60 * 60


def classify_trend_confidence(sample_count: int, years_covered: float, r2: float) -> str:
    if sample_count < 30 or years_covered < 1:
        return "low"
    if sample_count >= 1000 and years_covered >= 10 and r2 >= 0.5:
        return "high"
    if sample_count >= 365 and years_covered >= 3 and r2 >= 0.3:
        return "medium"
    return "low"


def _insufficient_trend(sample_count: int = 0, years_covered: float = 0.0) -> dict[str, object]:
    return {
        "trend": "insufficient_data",
        "slope_celsius_per_year": 0.0,
        "slope_celsius_per_decade": 0.0,
        "r2": 0.0,
        "sample_count": sample_count,
        "regression_points": 0,
        "years_covered": round(years_covered, 4),
        "confidence": "low",
    }


def _monthly_temperature_series(df: pd.DataFrame) -> pd.DataFrame:
    monthly = (
        df.set_index(TIMESTAMP_COLUMN)
        .resample("MS")
        .agg(temperature=(TEMPERATURE_COLUMN, "mean"), sample_count=(TEMPERATURE_COLUMN, "count"))
        .dropna(subset=["temperature"])
        .reset_index()
    )
    return monthly.loc[monthly["sample_count"] > 0].copy()


def compute_temperature_trend(df: pd.DataFrame) -> dict[str, object]:
    """Estimate linear temperature trend in Celsius per year."""

    if df.empty or TEMPERATURE_COLUMN not in df.columns:
        return _insufficient_trend()

    sample_count = int(df[TEMPERATURE_COLUMN].notna().sum())
    timestamps = df[TIMESTAMP_COLUMN].dropna()
    if sample_count < 2 or timestamps.empty:
        return _insufficient_trend(sample_count=sample_count)

    start = timestamps.min()
    end = timestamps.max()
    years_covered = float((end - start).total_seconds() / SECONDS_PER_YEAR)
    monthly = _monthly_temperature_series(df)
    if len(monthly) < 2 or years_covered <= 0:
        return _insufficient_trend(sample_count=sample_count, years_covered=years_covered)

    x = (monthly[TIMESTAMP_COLUMN] - start).dt.total_seconds().to_numpy(dtype=float) / SECONDS_PER_YEAR
    y = monthly["temperature"].to_numpy(dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    predicted = slope * x + intercept
    residual_sum = float(np.sum((y - predicted) ** 2))
    total_sum = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 0.0 if total_sum == 0 else max(0.0, 1.0 - residual_sum / total_sum)

    if slope > 0.03:
        trend = "increasing"
    elif slope < -0.03:
        trend = "decreasing"
    else:
        trend = "stable"

    confidence = classify_trend_confidence(sample_count=sample_count, years_covered=years_covered, r2=r2)
    LOGGER.info(
        "[CLIMATE] Trend slope: %+0.4f C/year, confidence=%s",
        slope,
        confidence,
    )
    return {
        "trend": trend,
        "slope_celsius_per_year": round(float(slope), 6),
        "slope_celsius_per_decade": round(float(slope * 10), 6),
        "r2": round(float(r2), 4),
        "sample_count": sample_count,
        "regression_points": int(len(monthly)),
        "years_covered": round(years_covered, 4),
        "confidence": confidence,
    }
