from __future__ import annotations

from datetime import date

import pandas as pd

from aeris.climate.aggregation import aggregate_annual, aggregate_monthly, aggregate_regional
from aeris.climate.anomalies import annual_anomalies, compute_anomalies, compute_monthly_baseline
from aeris.climate.regions import BAIXADA_SANTISTA
from aeris.climate.trend import linear_trend
from aeris.config import AerisPaths
from aeris.core.cache import CacheManager
from aeris.dataset.labels import infer_weather_label


def test_aeris_paths_create_scalable_layout(tmp_path):
    paths = AerisPaths.from_root(tmp_path / "datasets").ensure()

    assert paths.raw_sentinel2.exists()
    assert paths.raw_landsat.exists()
    assert paths.raw_weather.exists()
    assert paths.labels_verified.exists()
    assert paths.exports.exists()


def test_cache_manager_roundtrip(tmp_path):
    cache = CacheManager(tmp_path / "cache")
    payload = {"city": "santos", "year": 2023}

    assert cache.load_json("openmeteo", payload) is None
    cache.save_json("openmeteo", payload, {"ok": True})

    assert cache.load_json("openmeteo", payload) == {"ok": True}


def test_baixada_santista_region_has_expected_cities():
    cities = {coordinate.name for coordinate in BAIXADA_SANTISTA.coordinates}

    assert "santos" in cities
    assert "guaruja" in cities
    assert "peruibe" in cities
    assert BAIXADA_SANTISTA.bbox[0] < BAIXADA_SANTISTA.bbox[2]


def test_trend_returns_p_value_and_ci():
    annual = pd.DataFrame(
        {
            "year": list(range(2000, 2020)),
            "temperature_mean": [20.0 + index * 0.12 for index in range(20)],
            "coverage_ratio": [1.0] * 20,
        },
    )

    result = linear_trend(annual)

    assert result.slope_per_decade is not None
    assert result.slope_per_decade > 1.0
    assert result.p_value is not None
    assert result.ci95_low_per_decade is not None
    assert result.ci95_high_per_decade is not None


def test_monthly_anomalies_use_configurable_baseline():
    timestamps = pd.date_range("1961-01-01", periods=36, freq="YS")
    hourly_like = pd.DataFrame(
        {
            "timestamp_weather": timestamps,
            "city": ["regional"] * len(timestamps),
            "temperature_2m": [20.0] * 30 + [22.0] * 6,
            "precipitation": [0.0] * len(timestamps),
            "relative_humidity_2m": [80.0] * len(timestamps),
            "dew_point_2m": [18.0] * len(timestamps),
            "surface_pressure": [1014.0] * len(timestamps),
            "pressure_msl": [1016.0] * len(timestamps),
            "cloud_cover": [50.0] * len(timestamps),
            "shortwave_radiation": [300.0] * len(timestamps),
            "wind_speed_10m": [8.0] * len(timestamps),
        },
    )
    monthly = aggregate_monthly(hourly_like)
    regional = aggregate_regional(monthly, ["year", "month"])
    baseline = compute_monthly_baseline(regional, baseline_start_year=1961, baseline_end_year=1990)

    anomalies = compute_anomalies(regional, baseline)
    annual = annual_anomalies(anomalies)

    recent = annual.loc[annual["year"] >= 1991]
    assert recent["temperature_anomaly"].mean() > 0


def test_weather_label_heuristics_do_not_treat_era5_as_image():
    label, confidence = infer_weather_label(
        {
            "temperature_2m": 24.0,
            "dew_point_2m": 23.5,
            "relative_humidity_2m": 98.0,
            "cloud_cover": 94.0,
            "precipitation": 0.0,
        },
    )

    assert label == "fog"
    assert confidence > 0.7
