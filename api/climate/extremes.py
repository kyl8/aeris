from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from .loader import TEMPERATURE_COLUMN, TIMESTAMP_COLUMN


LOGGER = logging.getLogger("aeris.climate.extremes")


def _empty_extremes() -> dict[str, object]:
    return {
        "p90_temperature": None,
        "p95_temperature": None,
        "hot_records_p90": 0,
        "hot_records_p95": 0,
        "hot_records_p90_ratio": 0.0,
        "hot_records_p95_ratio": 0.0,
        "hot_extreme_frequency": "insufficient_data",
        "monthly_frequency": [],
        "annual_frequency": [],
    }


def _frequency_records(df: pd.DataFrame, is_hot: pd.Series, freq: str) -> list[dict[str, object]]:
    work_df = df[[TIMESTAMP_COLUMN]].copy()
    work_df["is_hot"] = is_hot.astype(int).to_numpy()
    work_df = work_df.set_index(TIMESTAMP_COLUMN)
    grouped = work_df.resample(freq).agg(hot_records=("is_hot", "sum"), sample_count=("is_hot", "count"))
    grouped = grouped.loc[grouped["sample_count"] > 0].reset_index()
    grouped["hot_ratio"] = grouped["hot_records"] / grouped["sample_count"]
    if freq == "MS":
        grouped["period"] = grouped[TIMESTAMP_COLUMN].dt.strftime("%Y-%m")
    else:
        grouped["period"] = grouped[TIMESTAMP_COLUMN].dt.strftime("%Y")
    grouped["hot_records"] = grouped["hot_records"].astype(int)
    grouped["sample_count"] = grouped["sample_count"].astype(int)
    grouped["hot_ratio"] = grouped["hot_ratio"].round(4)
    return grouped[["period", "hot_records", "sample_count", "hot_ratio"]].to_dict(orient="records")


def _classify_extreme_frequency(annual_frequency: list[dict[str, object]]) -> str:
    if len(annual_frequency) < 2:
        return "insufficient_data"

    x = np.arange(len(annual_frequency), dtype=float)
    y = np.array([float(record["hot_ratio"]) for record in annual_frequency], dtype=float)
    if np.allclose(y, y[0]):
        return "stable"
    slope = float(np.polyfit(x, y, 1)[0])
    if slope > 0.01:
        return "increasing"
    if slope < -0.01:
        return "decreasing"
    return "stable"


def compute_hot_extremes(df: pd.DataFrame) -> dict[str, object]:
    """Calculate P90/P95 heat extremes and temporal frequency."""

    if df.empty or TEMPERATURE_COLUMN not in df.columns:
        return _empty_extremes()

    temperatures = df[TEMPERATURE_COLUMN].dropna()
    if temperatures.empty:
        return _empty_extremes()

    p90 = float(temperatures.quantile(0.90))
    p95 = float(temperatures.quantile(0.95))
    hot_p90 = df[TEMPERATURE_COLUMN] >= p90
    hot_p95 = df[TEMPERATURE_COLUMN] >= p95
    total = int(temperatures.count())
    p90_count = int(hot_p90.sum())
    p95_count = int(hot_p95.sum())
    monthly_frequency = _frequency_records(df, hot_p90, "MS")
    annual_frequency = _frequency_records(df, hot_p90, "YS")
    frequency_label = _classify_extreme_frequency(annual_frequency)

    LOGGER.info("[CLIMATE] Hot extremes: P90=%0.2f C, P95=%0.2f C", p90, p95)
    return {
        "p90_temperature": round(p90, 4),
        "p95_temperature": round(p95, 4),
        "hot_records_p90": p90_count,
        "hot_records_p95": p95_count,
        "hot_records_p90_ratio": round(p90_count / total, 4),
        "hot_records_p95_ratio": round(p95_count / total, 4),
        "hot_extreme_frequency": frequency_label,
        "monthly_frequency": monthly_frequency,
        "annual_frequency": annual_frequency,
    }
