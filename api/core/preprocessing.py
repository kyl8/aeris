from base64 import b64decode, b64encode
from binascii import Error as Base64Error
from html import escape
import hashlib
from math import sqrt


def decode_base64_image(raw_value: str) -> bytes:
    cleaned_value = raw_value.strip()
    if cleaned_value.startswith("data:") and "," in cleaned_value:
        cleaned_value = cleaned_value.split(",", 1)[1].strip()

    try:
        return b64decode(cleaned_value, validate=False)
    except Base64Error as exc:
        raise ValueError("A imagem em base64 é inválida.") from exc


def validate_image_bytes(image_bytes: bytes) -> str:
    if not image_bytes:
        raise ValueError("A imagem enviada está vazia.")

    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"

    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "jpeg"

    if image_bytes.startswith(b"GIF87a") or image_bytes.startswith(b"GIF89a"):
        return "gif"

    if image_bytes.startswith(b"BM"):
        return "bmp"

    if len(image_bytes) >= 12 and image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "webp"

    if image_bytes.startswith(b"II*\x00") or image_bytes.startswith(b"MM\x00*"):
        return "tiff"

    if image_bytes[:4] == b"\x00\x00\x01\x00":
        return "ico"

    if image_bytes[:4] == b"\x00\x00\x02\x00":
        return "cur"

    if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"

    if image_bytes[:2] == b"P4" or image_bytes[:2] == b"P5" or image_bytes[:2] == b"P6":
        return "pnm"

    if image_bytes[:4] in {b"\x00\x00\x00\x0c", b"\x00\x00\x00\x14"} and b"ftyp" in image_bytes[:16]:
        return "heic"

    if len(image_bytes) < 8:
        raise ValueError("A imagem enviada não parece ser um arquivo compatível.")

    raise ValueError("A imagem enviada não parece ser um arquivo compatível.")


def _average(values: list[int]) -> float:
    if not values:
        return 0.0

    return sum(values) / len(values)


def _score_to_hex(start_rgb: tuple[int, int, int], end_rgb: tuple[int, int, int], score: float) -> str:
    clamped_score = max(0.0, min(score, 1.0))
    red = round(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * clamped_score)
    green = round(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * clamped_score)
    blue = round(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * clamped_score)
    return f"#{red:02x}{green:02x}{blue:02x}"


def extract_image_profile(image_bytes: bytes) -> dict[str, float]:
    validate_image_bytes(image_bytes)

    sample = list(image_bytes[:8192])
    if not sample:
        raise ValueError("A imagem enviada está vazia.")

    sample_length = len(sample)
    brightness = _average(sample)
    variance = _average([(value - brightness) ** 2 for value in sample])
    transitions = sum(1 for left, right in zip(sample, sample[1:]) if left != right)
    digest = hashlib.blake2b(image_bytes, digest_size=8).digest()

    return {
        "brightness": round(float(brightness), 4),
        "contrast": round(float(sqrt(variance)), 4),
        "saturation": round(float((len(set(sample)) / 256.0) * 255.0), 4),
        "edge_strength": round(float((transitions / max(sample_length - 1, 1)) * 255.0), 4),
        "red": round(float(_average(sample[0::3])), 4),
        "green": round(float(_average(sample[1::3])), 4),
        "blue": round(float(_average(sample[2::3])), 4),
        "digest": round(float(int.from_bytes(digest, "big") / 2**64 * 255.0), 4),
    }


def build_heatmap_base64(image_bytes: bytes, image_size: int = 320) -> str:
    profile = extract_image_profile(image_bytes)
    brightness_score = profile["brightness"] / 255.0
    contrast_score = profile["contrast"] / 128.0
    saturation_score = profile["saturation"] / 255.0
    digest_score = profile["digest"] / 255.0

    background_top = _score_to_hex((8, 12, 24), (38, 68, 132), brightness_score)
    background_bottom = _score_to_hex((14, 23, 46), (236, 72, 153), digest_score)
    first_bar = _score_to_hex((37, 99, 235), (250, 204, 21), brightness_score)
    second_bar = _score_to_hex((34, 197, 94), (239, 68, 68), contrast_score)
    third_bar = _score_to_hex((14, 165, 233), (168, 85, 247), saturation_score)

    bar_width = 52
    gap = 20
    left_margin = 30
    bottom = image_size - 44
    max_bar_height = 150

    bars = [
        ("brightness", brightness_score, first_bar),
        ("contrast", min(contrast_score, 1.0), second_bar),
        ("saturation", min(saturation_score, 1.0), third_bar),
    ]

    bars_markup = []
    for index, (label, score, fill_color) in enumerate(bars):
        height = round(max_bar_height * max(0.15, min(score, 1.0)))
        x_position = left_margin + index * (bar_width + gap)
        y_position = bottom - height
        bars_markup.append(
            f'<rect x="{x_position}" y="{y_position}" width="{bar_width}" height="{height}" rx="18" fill="{fill_color}" />'
        )
        bars_markup.append(
            f'<text x="{x_position + bar_width / 2}" y="{bottom + 22}" text-anchor="middle" fill="#e2e8f0" font-family="Segoe UI, Arial, sans-serif" font-size="12">{escape(label)}</text>'
        )

    svg = f'''
<svg xmlns="http://www.w3.org/2000/svg" width="{image_size}" height="{image_size}" viewBox="0 0 {image_size} {image_size}" role="img" aria-label="Aeris heatmap">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{background_top}" />
      <stop offset="100%" stop-color="{background_bottom}" />
    </linearGradient>
    <radialGradient id="glow" cx="35%" cy="32%" r="68%">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="0.22" />
      <stop offset="100%" stop-color="#ffffff" stop-opacity="0" />
    </radialGradient>
  </defs>
  <rect width="100%" height="100%" rx="32" fill="url(#bg)" />
  <circle cx="88" cy="72" r="96" fill="url(#glow)" />
  <circle cx="238" cy="242" r="76" fill="#ffffff" opacity="0.08" />
  <rect x="22" y="24" width="{image_size - 44}" height="{image_size - 48}" rx="28" fill="#0f172a" opacity="0.34" />
  <g opacity="0.9">
    {''.join(bars_markup)}
  </g>
  <text x="28" y="40" fill="#ffffff" font-family="Segoe UI, Arial, sans-serif" font-size="18" font-weight="700">Heatmap</text>
  <text x="28" y="60" fill="#cbd5e1" font-family="Segoe UI, Arial, sans-serif" font-size="12">brightness · contrast · saturation</text>
</svg>
'''

    return b64encode(svg.encode("utf-8")).decode("ascii")
