from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageFilter, ImageStat


def _weather_value(weather: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = weather.get(key)
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def infer_weather_label(weather: dict[str, Any]) -> tuple[str, float]:
    precipitation = _weather_value(weather, "precipitation")
    rain = _weather_value(weather, "rain")
    snowfall = _weather_value(weather, "snowfall")
    cloud_cover = _weather_value(weather, "cloud_cover")
    humidity = _weather_value(weather, "relative_humidity_2m")
    temperature = _weather_value(weather, "temperature_2m")
    dew_point = _weather_value(weather, "dew_point_2m")
    wind_gusts = _weather_value(weather, "wind_gusts_10m")
    weather_code = int(_weather_value(weather, "weather_code", -1))
    dewpoint_spread = temperature - dew_point

    if weather_code in {95, 96, 99} or (precipitation >= 8.0 and wind_gusts >= 45):
        return "storm", 0.86
    if snowfall > 0.0 or temperature <= 0 and precipitation > 0:
        return "snow", 0.82
    if temperature <= 1.5 and humidity >= 80 and precipitation <= 0.2:
        return "frost", 0.72
    if precipitation >= 0.4 or rain >= 0.4 or weather_code in {51, 53, 55, 61, 63, 65, 80, 81, 82}:
        return "rain", min(0.92, 0.6 + precipitation / 20.0)
    if humidity >= 95 and dewpoint_spread <= 1.5 and cloud_cover >= 70:
        return "fog", 0.83
    if humidity >= 90 and dewpoint_spread <= 2.5:
        return "mist", 0.74
    if cloud_cover >= 90:
        return "overcast", 0.84
    if cloud_cover >= 55:
        return "cloudy", 0.75
    if humidity >= 75 and cloud_cover >= 35:
        return "haze", 0.55
    return "clear", 0.78


def image_statistics(image_path: str | Path) -> dict[str, float]:
    with Image.open(image_path) as image:
        rgb = image.convert("RGB").resize((256, 256))
        gray = rgb.convert("L")
        stat = ImageStat.Stat(rgb)
        gray_stat = ImageStat.Stat(gray)
        edges = gray.filter(ImageFilter.FIND_EDGES)
        edge_stat = ImageStat.Stat(edges)
        array = np.asarray(gray, dtype=np.float32)
        return {
            "brightness": float(gray_stat.mean[0]),
            "contrast": float(gray_stat.stddev[0]),
            "edge_density": float(edge_stat.mean[0]),
            "red_mean": float(stat.mean[0]),
            "green_mean": float(stat.mean[1]),
            "blue_mean": float(stat.mean[2]),
            "dark_ratio": float((array < 25).mean()),
            "bright_ratio": float((array > 230).mean()),
        }


def infer_visual_label(image_path: str | Path, weather: dict[str, Any] | None = None) -> tuple[str, float, dict[str, float]]:
    weather = weather or {}
    stats = image_statistics(image_path)
    brightness = stats["brightness"]
    contrast = stats["contrast"]
    edge_density = stats["edge_density"]
    blue_mean = stats["blue_mean"]
    red_mean = stats["red_mean"]
    cloud_cover = _weather_value(weather, "cloud_cover")
    humidity = _weather_value(weather, "relative_humidity_2m")
    precipitation = _weather_value(weather, "precipitation")

    if precipitation >= 8:
        return "storm", 0.68, stats
    if precipitation >= 0.4:
        return "rain", 0.66, stats
    if humidity >= 95 and contrast < 32 and edge_density < 25:
        return "fog", 0.78, stats
    if humidity >= 88 and contrast < 38:
        return "mist", 0.64, stats
    if cloud_cover >= 90 or (brightness > 175 and contrast < 45 and edge_density < 32):
        return "overcast", 0.76, stats
    if cloud_cover >= 55 or (brightness > 150 and contrast < 55):
        return "cloudy", 0.68, stats
    if red_mean > blue_mean + 18 and contrast < 45:
        return "haze", 0.56, stats
    if brightness < 45:
        return "haze", 0.45, stats
    return "clear", 0.72, stats


def quality_flags(weather: dict[str, Any], image_stats: dict[str, float] | None = None) -> dict[str, bool]:
    image_stats = image_stats or {}
    cloud_cover = _weather_value(weather, "cloud_cover")
    shortwave = _weather_value(weather, "shortwave_radiation")
    return {
        "cloud_artifact": cloud_cover >= 98,
        "sensor_issue": bool(image_stats.get("dark_ratio", 0.0) > 0.85 or image_stats.get("bright_ratio", 0.0) > 0.85),
        "low_visibility": bool(_weather_value(weather, "relative_humidity_2m") >= 95 and _weather_value(weather, "cloud_cover") >= 80),
        "night": shortwave <= 1,
    }
