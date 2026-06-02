from __future__ import annotations

import logging

import pandas as pd

from .loader import TEMPERATURE_COLUMN, TIMESTAMP_COLUMN


LOGGER = logging.getLogger("aeris.climate.baseline")

BASELINE_COLUMNS = [
    "month",
    "baseline_temperature_mean",
    "baseline_temperature_std",
    "baseline_temperature_min",
    "baseline_temperature_max",
    "sample_count",
]


def compute_monthly_baseline(df: pd.DataFrame) -> pd.DataFrame:
    """Compute historical baseline temperature by month of year."""

    if df.empty:
        return pd.DataFrame(columns=BASELINE_COLUMNS)

    work_df = df.copy()
    work_df["month"] = work_df[TIMESTAMP_COLUMN].dt.month

    baseline = (
        work_df.groupby("month")
        .agg(
            baseline_temperature_mean=(TEMPERATURE_COLUMN, "mean"),
            baseline_temperature_std=(TEMPERATURE_COLUMN, "std"),
            baseline_temperature_min=(TEMPERATURE_COLUMN, "min"),
            baseline_temperature_max=(TEMPERATURE_COLUMN, "max"),
            sample_count=(TEMPERATURE_COLUMN, "count"),
        )
        .reset_index()
    )
    baseline["baseline_temperature_std"] = baseline["baseline_temperature_std"].fillna(0.0)
    baseline = baseline[BASELINE_COLUMNS]

    LOGGER.info("[CLIMATE] Computed monthly baseline for %d months", len(baseline))
    return baseline
