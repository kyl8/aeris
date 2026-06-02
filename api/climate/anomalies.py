from __future__ import annotations

import math

import pandas as pd

from .loader import TEMPERATURE_COLUMN, TIMESTAMP_COLUMN


def classify_anomaly(value: float) -> str:
    if value is None or math.isnan(float(value)):
        return "unknown"
    if value >= 2.0:
        return "very_high"
    if value >= 1.0:
        return "high"
    if value <= -2.0:
        return "very_low"
    if value <= -1.0:
        return "low"
    return "normal"


def compute_temperature_anomalies(df: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    """Calculate temperature anomaly against the monthly baseline."""

    if df.empty:
        return df.copy()
    if baseline.empty:
        raise ValueError("Baseline mensal vazia. Nao e possivel calcular anomalias.")

    work_df = df.copy()
    work_df["month"] = work_df[TIMESTAMP_COLUMN].dt.month
    merged = work_df.merge(
        baseline[
            [
                "month",
                "baseline_temperature_mean",
                "baseline_temperature_std",
            ]
        ],
        on="month",
        how="left",
    )
    merged["temperature_anomaly"] = merged[TEMPERATURE_COLUMN] - merged["baseline_temperature_mean"]
    merged["anomaly_level"] = merged["temperature_anomaly"].map(classify_anomaly)
    return merged


def summarize_temperature_anomalies(anomalies: pd.DataFrame) -> dict[str, object]:
    if anomalies.empty or "temperature_anomaly" not in anomalies.columns:
        return {
            "latest_anomaly_celsius": None,
            "latest_anomaly_level": "unknown",
            "positive_anomaly_ratio": 0.0,
            "positive_anomaly_frequency": "insufficient_data",
        }

    ordered = anomalies.sort_values(TIMESTAMP_COLUMN)
    latest = ordered.iloc[-1]
    positive_ratio = float((ordered["temperature_anomaly"] > 0).mean())
    if positive_ratio >= 0.6:
        frequency = "above_normal"
    elif positive_ratio <= 0.4:
        frequency = "below_normal"
    else:
        frequency = "near_normal"

    return {
        "latest_anomaly_celsius": round(float(latest["temperature_anomaly"]), 4),
        "latest_anomaly_level": str(latest["anomaly_level"]),
        "positive_anomaly_ratio": round(positive_ratio, 4),
        "positive_anomaly_frequency": frequency,
    }
