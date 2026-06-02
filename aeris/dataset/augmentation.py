from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


@dataclass(frozen=True, slots=True)
class AugmentationConfig:
    rotations: tuple[int, ...] = (90, 180, 270)
    crop_scale: float = 0.86
    brightness: tuple[float, ...] = (0.82, 1.18)
    contrast: tuple[float, ...] = (0.85, 1.2)
    blur_radius: float = 1.2
    haze_strength: float = 0.22
    rain_strength: float = 0.35
    cloud_strength: float = 0.22
    atmospheric_noise: float = 0.035


def augment_image(input_path: str | Path, output_dir: str | Path, *, config: AugmentationConfig | None = None) -> list[Path]:
    config = config or AugmentationConfig()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []
    with Image.open(input_path) as image:
        base = ImageOps.exif_transpose(image).convert("RGB")
        stem = Path(input_path).stem
        for angle in config.rotations:
            generated.append(_save(base.rotate(angle, expand=True), output / f"{stem}_rot{angle}.jpg"))
        generated.append(_save(_center_crop_resize(base, config.crop_scale), output / f"{stem}_crop.jpg"))
        for factor in config.brightness:
            generated.append(_save(ImageEnhance.Brightness(base).enhance(factor), output / f"{stem}_brightness_{factor:.2f}.jpg"))
        for factor in config.contrast:
            generated.append(_save(ImageEnhance.Contrast(base).enhance(factor), output / f"{stem}_contrast_{factor:.2f}.jpg"))
        generated.append(_save(base.filter(ImageFilter.GaussianBlur(radius=config.blur_radius)), output / f"{stem}_blur.jpg"))
        generated.append(_save(_haze(base, config.haze_strength), output / f"{stem}_haze.jpg"))
        generated.append(_save(_rain(base, config.rain_strength), output / f"{stem}_rain.jpg"))
        generated.append(_save(_cloud_overlay(base, config.cloud_strength), output / f"{stem}_clouds.jpg"))
        generated.append(_save(_noise(base, config.atmospheric_noise), output / f"{stem}_noise.jpg"))
    return generated


def _save(image: Image.Image, path: Path) -> Path:
    image.convert("RGB").save(path, format="JPEG", quality=92, optimize=True)
    return path


def _center_crop_resize(image: Image.Image, scale: float) -> Image.Image:
    width, height = image.size
    crop_w = int(width * scale)
    crop_h = int(height * scale)
    left = (width - crop_w) // 2
    top = (height - crop_h) // 2
    return image.crop((left, top, left + crop_w, top + crop_h)).resize((width, height), Image.Resampling.LANCZOS)


def _haze(image: Image.Image, strength: float) -> Image.Image:
    overlay = Image.new("RGB", image.size, (230, 235, 238))
    return Image.blend(image, overlay, strength)


def _cloud_overlay(image: Image.Image, strength: float) -> Image.Image:
    width, height = image.size
    rng = np.random.default_rng(42)
    noise = rng.normal(160, 55, (height, width)).clip(0, 255).astype(np.uint8)
    mask = Image.fromarray(noise, mode="L").filter(ImageFilter.GaussianBlur(radius=max(width, height) / 55))
    clouds = Image.new("RGB", image.size, (245, 245, 245))
    blended = Image.composite(clouds, image, mask.point(lambda value: int(value * strength)))
    return Image.blend(image, blended, strength)


def _rain(image: Image.Image, strength: float) -> Image.Image:
    width, height = image.size
    rain = Image.new("RGBA", image.size, (0, 0, 0, 0))
    pixels = rain.load()
    random.seed(42)
    drops = int(width * height * 0.002 * strength)
    for _ in range(drops):
        x = random.randrange(width)
        y = random.randrange(height)
        length = random.randrange(8, 22)
        for offset in range(length):
            xx = min(width - 1, x + offset // 3)
            yy = min(height - 1, y + offset)
            pixels[xx, yy] = (210, 220, 230, 110)
    rain = rain.filter(ImageFilter.GaussianBlur(radius=0.5))
    return Image.alpha_composite(image.convert("RGBA"), rain).convert("RGB")


def _noise(image: Image.Image, strength: float) -> Image.Image:
    array = np.asarray(image).astype(np.float32)
    rng = np.random.default_rng(42)
    noise = rng.normal(0, 255 * strength, array.shape)
    return Image.fromarray(np.clip(array + noise, 0, 255).astype(np.uint8), mode="RGB")
