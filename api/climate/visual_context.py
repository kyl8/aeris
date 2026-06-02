from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, UnidentifiedImageError


def _empty_context(status: str, note: str) -> dict[str, object]:
    return {
        "scene": [],
        "cloud_status": "unknown",
        "image_quality": status,
        "notes": [note, "Imagem usada apenas como contexto visual."],
    }


def _ratio(mask: np.ndarray) -> float:
    if mask.size == 0:
        return 0.0
    return float(mask.mean())


def analyze_visual_context(image_path: str | None) -> dict[str, object]:
    """Analyze image context with lightweight heuristics.

    This intentionally avoids climate conclusions. The image only describes
    scene context, cloud cover and quality hints.
    """

    if not image_path:
        return _empty_context("not_provided", "Nenhuma imagem foi fornecida para contexto visual.")

    path = Path(image_path)
    if not path.exists():
        return _empty_context("missing", f"Imagem nao encontrada: {path}")

    try:
        with Image.open(path) as image:
            rgb = image.convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        return _empty_context("invalid", f"Imagem invalida ou corrompida: {exc}")

    rgb.thumbnail((256, 256))
    arr = np.asarray(rgb, dtype=np.float32)
    red = arr[:, :, 0]
    green = arr[:, :, 1]
    blue = arr[:, :, 2]
    brightness = arr.mean(axis=2)
    channel_spread = arr.max(axis=2) - arr.min(axis=2)

    mean_brightness = float(brightness.mean())
    mean_spread = float(channel_spread.mean())
    bright_low_saturation = (brightness > 190) & (channel_spread < 35)
    ocean_mask = (blue > green + 12) & (blue > red + 18) & (brightness > 35)
    vegetation_mask = (green > red + 10) & (green > blue + 4) & (brightness > 30)
    urban_mask = (channel_spread < 45) & (brightness > 70) & (brightness < 190)

    cloud_ratio = _ratio(bright_low_saturation)
    ocean_ratio = _ratio(ocean_mask)
    vegetation_ratio = _ratio(vegetation_mask)
    urban_ratio = _ratio(urban_mask)

    scene: list[str] = []
    if ocean_ratio > 0.12:
        scene.append("ocean")
    if vegetation_ratio > 0.08:
        scene.append("vegetation")
    if urban_ratio > 0.18:
        scene.append("urban_area")
    if "ocean" in scene and ("vegetation" in scene or "urban_area" in scene):
        scene.insert(0, "coastal_region")
    if not scene:
        scene.append("remote_sensing_scene")

    if cloud_ratio >= 0.75:
        cloud_status = "mostly_cloudy_or_overexposed"
    elif cloud_ratio >= 0.35:
        cloud_status = "cloudy"
    elif cloud_ratio >= 0.12:
        cloud_status = "scattered_clouds"
    else:
        cloud_status = "mostly_clear"

    if mean_brightness > 235 and mean_spread < 20:
        quality = "overexposed"
    elif mean_brightness < 25:
        quality = "dark_or_low_information"
    elif mean_spread < 8:
        quality = "low_information"
    else:
        quality = "valid"

    notes = ["Imagem usada apenas como contexto visual."]
    if "coastal_region" in scene:
        notes.append("Imagem sugere regiao costeira com oceano e cobertura terrestre.")
    if cloud_status != "mostly_clear":
        notes.append("Cobertura de nuvens ou brilho elevado pode reduzir informacao visual.")
    if quality != "valid":
        notes.append("Qualidade visual limitada; nao usar como evidencia climatica direta.")

    return {
        "scene": scene,
        "cloud_status": cloud_status,
        "image_quality": quality,
        "metrics": {
            "brightness_mean": round(mean_brightness, 4),
            "color_spread_mean": round(mean_spread, 4),
            "cloud_like_ratio": round(cloud_ratio, 4),
            "ocean_like_ratio": round(ocean_ratio, 4),
            "vegetation_like_ratio": round(vegetation_ratio, 4),
            "urban_like_ratio": round(urban_ratio, 4),
        },
        "notes": notes,
    }
