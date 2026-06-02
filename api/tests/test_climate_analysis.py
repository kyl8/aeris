from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from api.climate.aggregation import aggregate_temperature
from api.climate.anomalies import compute_temperature_anomalies
from api.climate.baseline import compute_monthly_baseline
from api.climate.correlations import compute_climate_correlations
from api.climate.extremes import compute_hot_extremes
from api.climate.loader import load_climate_dataset
from api.climate.pipeline import analyze_global_warming_signal
from api.climate.report import generate_climate_report, generate_climate_warnings
from api.climate.trends import compute_temperature_trend


def _base_climate_df(timestamps: pd.DatetimeIndex, temperatures: list[float]) -> pd.DataFrame:
    row_count = len(timestamps)
    radiation = [300 + index * 20 for index in range(row_count)]
    return pd.DataFrame(
        {
            "arquivo_imagem": [f"image_{index}.jpg" for index in range(row_count)],
            "timestamp_imagem": timestamps.astype(str),
            "timestamp_meteorologico": timestamps,
            "latitude": [-23.9618] * row_count,
            "longitude": [-46.3322] * row_count,
            "classe_satelite": ["urban_area"] * row_count,
            "confianca_satelite": [0.8] * row_count,
            "classe_perspectiva": ["sun/clear"] * row_count,
            "confianca_perspectiva": [0.7] * row_count,
            "temperature_2m": temperatures,
            "relative_humidity_2m": [80 - index for index in range(row_count)],
            "dew_point_2m": [18 + index * 0.1 for index in range(row_count)],
            "precipitation": [0.0] * row_count,
            "surface_pressure": [1015.0] * row_count,
            "cloud_cover": [50.0] * row_count,
            "cloud_cover_low": [20.0] * row_count,
            "cloud_cover_mid": [20.0] * row_count,
            "cloud_cover_high": [10.0] * row_count,
            "shortwave_radiation": radiation,
            "direct_radiation": [value * 0.7 for value in radiation],
            "diffuse_radiation": [value * 0.3 for value in radiation],
            "wind_speed_10m": [8.0] * row_count,
            "wind_gusts_10m": [16.0] * row_count,
        },
    )


def _write_csv(tmp_path: Path, df: pd.DataFrame) -> Path:
    csv_path = tmp_path / "climate.csv"
    df.to_csv(csv_path, index=False)
    return csv_path


def test_load_climate_dataset_with_valid_timestamp(tmp_path: Path) -> None:
    df = _base_climate_df(pd.date_range("2023-01-01", periods=3, freq="D"), [24.0, 25.0, 26.0])
    csv_path = _write_csv(tmp_path, df)

    loaded = load_climate_dataset(csv_path)

    assert len(loaded) == 3
    assert pd.api.types.is_datetime64_any_dtype(loaded["timestamp_meteorologico"])


def test_load_climate_dataset_missing_required_column_raises(tmp_path: Path) -> None:
    df = _base_climate_df(pd.date_range("2023-01-01", periods=2, freq="D"), [24.0, 25.0])
    csv_path = _write_csv(tmp_path, df.drop(columns=["temperature_2m"]))

    with pytest.raises(ValueError, match="temperature_2m"):
        load_climate_dataset(csv_path)


def test_aggregate_temperature_monthly() -> None:
    df = _base_climate_df(pd.to_datetime(["2023-01-01", "2023-01-02", "2023-02-01"]), [24.0, 26.0, 30.0])

    result = aggregate_temperature(df, freq="M")

    assert list(result["period"]) == ["2023-01", "2023-02"]
    assert result.loc[0, "temperature_mean"] == 25.0
    assert result.loc[0, "sample_count"] == 2


def test_compute_monthly_baseline() -> None:
    df = _base_climate_df(pd.to_datetime(["2021-04-01", "2022-04-01", "2023-05-01"]), [24.0, 26.0, 30.0])

    baseline = compute_monthly_baseline(df)

    april = baseline.loc[baseline["month"] == 4].iloc[0]
    assert april["baseline_temperature_mean"] == 25.0
    assert april["sample_count"] == 2


def test_compute_temperature_anomaly_positive() -> None:
    df = _base_climate_df(pd.to_datetime(["2021-04-01", "2022-04-01", "2023-04-01"]), [24.0, 26.0, 28.0])
    baseline = compute_monthly_baseline(df.iloc[:2])

    anomalies = compute_temperature_anomalies(df.iloc[2:], baseline)

    assert anomalies.iloc[0]["temperature_anomaly"] == 3.0
    assert anomalies.iloc[0]["anomaly_level"] == "very_high"


def test_temperature_trend_increasing() -> None:
    df = _base_climate_df(pd.date_range("2020-01-01", periods=5, freq="YE"), [24.0, 24.2, 24.5, 24.7, 25.0])

    result = compute_temperature_trend(df)

    assert result["trend"] == "increasing"
    assert result["slope_celsius_per_year"] > 0


def test_temperature_trend_stable() -> None:
    df = _base_climate_df(pd.date_range("2020-01-01", periods=5, freq="YE"), [24.0, 24.01, 24.0, 24.01, 24.0])

    result = compute_temperature_trend(df)

    assert result["trend"] == "stable"


def test_insufficient_data_confidence_low() -> None:
    df = _base_climate_df(pd.date_range("2023-01-01", periods=5, freq="D"), [25.0, 25.2, 25.1, 25.3, 25.4])

    result = compute_temperature_trend(df)

    assert result["confidence"] == "low"


def test_compute_hot_extremes_p90_p95() -> None:
    df = _base_climate_df(pd.date_range("2023-01-01", periods=20, freq="D"), [20.0 + index for index in range(20)])

    result = compute_hot_extremes(df)

    assert result["p90_temperature"] > 36
    assert result["hot_records_p90"] > 0
    assert result["hot_records_p95"] > 0


def test_compute_climate_correlations() -> None:
    df = _base_climate_df(pd.date_range("2023-01-01", periods=10, freq="D"), [20.0 + index for index in range(10)])

    result = compute_climate_correlations(df)

    assert result["correlations"]["shortwave_radiation"] > 0.9
    assert result["interpretation"]


def test_generate_warnings_for_short_series() -> None:
    df = _base_climate_df(pd.date_range("2023-01-01", periods=5, freq="D"), [25.0, 25.1, 25.2, 25.3, 25.4])
    trend = compute_temperature_trend(df)

    warnings = generate_climate_warnings(df, trend)

    assert any("Serie historica curta" in warning for warning in warnings)
    assert any("Imagem isolada" in warning for warning in warnings)


def test_generate_human_report(tmp_path: Path) -> None:
    df = _base_climate_df(pd.date_range("2020-01-01", periods=12, freq="MS"), [24.0 + index * 0.1 for index in range(12)])
    csv_path = _write_csv(tmp_path, df)

    result = analyze_global_warming_signal(csv_path, region_name="Litoral SP")
    report = generate_climate_report(result)

    assert "Aeris Climate Report" in report
    assert "Litoral SP" in report
    assert "Imagem" in report
