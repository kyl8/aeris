from __future__ import annotations

import pandas as pd


def compute_monthly_baseline(
    monthly_summary: pd.DataFrame,
    *,
    baseline_start_year: int = 1961,
    baseline_end_year: int = 1990,
) -> pd.DataFrame:
    if monthly_summary.empty:
        return pd.DataFrame()
    subset = monthly_summary.loc[monthly_summary["year"].between(baseline_start_year, baseline_end_year)].copy()
    if subset.empty:
        return pd.DataFrame()
    baseline = (
        subset.groupby(["city", "month"], dropna=False)
        .agg(
            baseline_temperature_mean=("temperature_mean", "mean"),
            baseline_temperature_std=("temperature_mean", "std"),
            baseline_sample_count=("temperature_mean", "count"),
        )
        .reset_index()
    )
    baseline["baseline_temperature_std"] = baseline["baseline_temperature_std"].fillna(0.0)
    baseline["baseline_start_year"] = baseline_start_year
    baseline["baseline_end_year"] = baseline_end_year
    return baseline


def compute_anomalies(monthly_summary: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    if monthly_summary.empty or baseline.empty:
        return pd.DataFrame()
    merged = monthly_summary.merge(
        baseline[
            [
                "city",
                "month",
                "baseline_temperature_mean",
                "baseline_temperature_std",
                "baseline_sample_count",
                "baseline_start_year",
                "baseline_end_year",
            ]
        ],
        on=["city", "month"],
        how="left",
    )
    merged["temperature_anomaly"] = merged["temperature_mean"] - merged["baseline_temperature_mean"]
    merged["temperature_anomaly_zscore"] = merged.apply(
        lambda row: (
            row["temperature_anomaly"] / row["baseline_temperature_std"]
            if pd.notna(row["baseline_temperature_std"]) and row["baseline_temperature_std"] > 0
            else pd.NA
        ),
        axis=1,
    )
    merged["anomaly_level"] = merged["temperature_anomaly"].map(classify_anomaly)
    return merged


def annual_anomalies(monthly_anomalies: pd.DataFrame) -> pd.DataFrame:
    if monthly_anomalies.empty:
        return pd.DataFrame()
    return (
        monthly_anomalies.groupby(["city", "year"], dropna=False)
        .agg(
            temperature_anomaly=("temperature_anomaly", "mean"),
            positive_months=("temperature_anomaly", lambda values: int((values > 0).sum())),
            negative_months=("temperature_anomaly", lambda values: int((values < 0).sum())),
            months=("temperature_anomaly", "count"),
        )
        .reset_index()
    )


def classify_anomaly(value: float | None) -> str:
    if value is None or pd.isna(value):
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


def top_anomaly_years(annual: pd.DataFrame, *, n: int = 10) -> tuple[pd.DataFrame, pd.DataFrame]:
    if annual.empty:
        return pd.DataFrame(), pd.DataFrame()
    regional = annual.copy()
    if "city" in regional.columns:
        regional = regional.loc[regional["city"] == "regional"] if "regional" in set(regional["city"]) else regional
    warmest = regional.sort_values("temperature_anomaly", ascending=False).head(n)
    coldest = regional.sort_values("temperature_anomaly", ascending=True).head(n)
    return warmest, coldest


def detect_outliers(monthly_anomalies: pd.DataFrame, annual_anomaly_summary: pd.DataFrame) -> dict[str, list[dict[str, object]]]:
    if monthly_anomalies.empty:
        return {"hot_months": [], "cold_months": [], "hot_years": [], "cold_years": []}
    hot_months = monthly_anomalies.loc[monthly_anomalies["temperature_anomaly"] >= 2.0]
    cold_months = monthly_anomalies.loc[monthly_anomalies["temperature_anomaly"] <= -2.0]
    hot_years = annual_anomaly_summary.loc[annual_anomaly_summary["temperature_anomaly"] >= 1.0] if not annual_anomaly_summary.empty else pd.DataFrame()
    cold_years = annual_anomaly_summary.loc[annual_anomaly_summary["temperature_anomaly"] <= -1.0] if not annual_anomaly_summary.empty else pd.DataFrame()
    return {
        "hot_months": hot_months.sort_values("temperature_anomaly", ascending=False).head(50).to_dict(orient="records"),
        "cold_months": cold_months.sort_values("temperature_anomaly", ascending=True).head(50).to_dict(orient="records"),
        "hot_years": hot_years.sort_values("temperature_anomaly", ascending=False).head(20).to_dict(orient="records"),
        "cold_years": cold_years.sort_values("temperature_anomaly", ascending=True).head(20).to_dict(orient="records"),
    }
