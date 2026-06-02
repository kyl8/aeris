from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image, UnidentifiedImageError


def file_sha256(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_image_file(path: str | Path) -> tuple[bool, str | None]:
    candidate = Path(path)
    if not candidate.exists():
        return False, "missing_file"
    if candidate.stat().st_size == 0:
        return False, "empty_file"
    try:
        with Image.open(candidate) as image:
            image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        return False, f"invalid_image:{exc}"
    return True, None
