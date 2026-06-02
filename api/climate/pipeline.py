from __future__ import annotations

import argparse
import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .aggregation import aggregate_temperature
from .anomalies import compute_temperature_anomalies, summarize_temperature_anomalies
from .baseline import compute_monthly_baseline
from .correlations import compute_climate_correlations
from .extremes import compute_hot_extremes
from .loader import TEMPERATURE_COLUMN, TIMESTAMP_COLUMN, load_climate_dataset
from .report import build_final_assessment, generate_climate_report, generate_climate_warnings
from .trends import compute_temperature_trend
from .visual_context import analyze_visual_context


LOGGER = logging.getLogger("aeris.climate.pipeline")


def _json_safe(value: Any) -> Any:
    if value is pd.NA:
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _records(df: pd.DataFrame, limit: int | None = None) -> list[dict[str, Any]]:
    if df.empty:
        return []
    output_df = df.copy()
    if limit is not None:
        output_df = output_df.tail(limit)
    output_df = output_df.replace({np.nan: None})
    return _json_safe(output_df.to_dict(orient="records"))


def _temperature_summary(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {"mean": None, "min": None, "max": None, "std": None}
    temperature = df[TEMPERATURE_COLUMN]
    return {
        "mean": round(float(temperature.mean()), 4),
        "min": round(float(temperature.min()), 4),
        "max": round(float(temperature.max()), 4),
        "std": round(float(temperature.std(ddof=0)), 4),
    }


def _period_summary(df: pd.DataFrame, years_covered: float) -> dict[str, Any]:
    if df.empty:
        return {"start": None, "end": None, "years_covered": 0.0}
    return {
        "start": df[TIMESTAMP_COLUMN].min().date().isoformat(),
        "end": df[TIMESTAMP_COLUMN].max().date().isoformat(),
        "years_covered": round(float(years_covered), 4),
    }


def _coordinates_summary(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {"latitude_mean": None, "longitude_mean": None}
    return {
        "latitude_mean": round(float(df["latitude"].mean()), 6),
        "longitude_mean": round(float(df["longitude"].mean()), 6),
    }


def _anomaly_distribution(anomalies: pd.DataFrame) -> dict[str, int]:
    if anomalies.empty or "anomaly_level" not in anomalies.columns:
        return {}
    return {str(key): int(value) for key, value in anomalies["anomaly_level"].value_counts().items()}


def analyze_global_warming_signal(
    csv_path: str | Path,
    region_name: str | None = None,
    image_path: str | None = None,
) -> dict[str, Any]:
    """Run the complete Aeris Climate analysis pipeline."""

    df = load_climate_dataset(csv_path)
    monthly_aggregation = aggregate_temperature(df, freq="M")
    annual_aggregation = aggregate_temperature(df, freq="Y")
    baseline = compute_monthly_baseline(df)
    anomalies = compute_temperature_anomalies(df, baseline) if not df.empty else pd.DataFrame()
    anomaly_summary = summarize_temperature_anomalies(anomalies)
    anomaly_summary["distribution"] = _anomaly_distribution(anomalies)
    trend_result = compute_temperature_trend(df)
    extremes_result = compute_hot_extremes(df)
    correlations_result = compute_climate_correlations(df)
    visual_context = analyze_visual_context(image_path)
    final_assessment = build_final_assessment(trend_result, anomaly_summary, extremes_result)
    warnings = generate_climate_warnings(df, trend_result)

    result: dict[str, Any] = {
        "region": region_name or "Baixada Santista / Litoral SP",
        "coordinates": _coordinates_summary(df),
        "period": _period_summary(df, float(trend_result.get("years_covered") or 0)),
        "temperature_summary": _temperature_summary(df),
        "trend_analysis": trend_result,
        "anomaly_analysis": anomaly_summary,
        "hot_extremes": extremes_result,
        "drivers": correlations_result,
        "visual_context": visual_context,
        "final_assessment": final_assessment,
        "warnings": warnings,
        "aggregations": {
            "monthly": _records(monthly_aggregation),
            "annual": _records(annual_aggregation),
        },
        "baseline": _records(baseline),
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "csv_path": str(csv_path),
            "image_path": image_path,
            "method": "linear_trend_monthly_temperature_plus_monthly_baseline_anomalies",
        },
    }
    result["human_report"] = generate_climate_report(result)
    LOGGER.info("[CLIMATE] Final assessment: %s", final_assessment["label"])
    return _json_safe(result)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Aeris Climate analysis over a multimodal CSV.")
    parser.add_argument("--csv", required=True, help="Path to Aeris climate multimodal CSV.")
    parser.add_argument("--region", default=None, help="Human-readable region name.")
    parser.add_argument("--image", default=None, help="Optional image path for visual context.")
    parser.add_argument("--output", type=Path, default=None, help="Optional JSON output path.")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = parse_args()
    result = analyze_global_warming_signal(args.csv, region_name=args.region, image_path=args.image)
    print(generate_climate_report(result))
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
