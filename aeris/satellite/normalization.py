from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PIL import Image, ImageOps


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def normalize_rgb_image(input_path: str | Path, output_path: str | Path, *, size: int = 512) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(input_path) as image:
        rgb = ImageOps.exif_transpose(image).convert("RGB")
        rgb.thumbnail((size, size), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (size, size), (0, 0, 0))
        canvas.paste(rgb, ((size - rgb.width) // 2, (size - rgb.height) // 2))
        canvas.save(output, format="JPEG", quality=92, optimize=True)
    return output


def create_thumbnail(input_path: str | Path, output_path: str | Path, *, size: int = 256) -> Path:
    return normalize_rgb_image(input_path, output_path, size=size)


def tile_image(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    tile_size: int = 224,
    stride: int | None = None,
) -> list[Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    stride = stride or tile_size
    tiles: list[Path] = []
    with Image.open(input_path) as image:
        rgb = ImageOps.exif_transpose(image).convert("RGB")
        width, height = rgb.size
        for top in range(0, max(1, height - tile_size + 1), stride):
            for left in range(0, max(1, width - tile_size + 1), stride):
                crop = rgb.crop((left, top, min(left + tile_size, width), min(top + tile_size, height)))
                if crop.size != (tile_size, tile_size):
                    padded = Image.new("RGB", (tile_size, tile_size), (0, 0, 0))
                    padded.paste(crop, (0, 0))
                    crop = padded
                tile_path = output / f"{Path(input_path).stem}_y{top}_x{left}.jpg"
                crop.save(tile_path, format="JPEG", quality=92, optimize=True)
                tiles.append(tile_path)
    return tiles


def iter_images(paths: Iterable[str | Path]) -> list[Path]:
    return sorted(path for path in (Path(item) for item in paths) if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS)
