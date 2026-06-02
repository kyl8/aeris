"""Build a multimodal climate dataset for Santos/SP historical images.

The pipeline combines two Hugging Face vision classifiers with hourly
meteorological observations from the Open-Meteo Historical Weather API.
It is intentionally standalone and does not import the FastAPI application.
"""

from __future__ import annotations

import argparse
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import pandas as pd
import requests
import torch
from PIL import Image, UnidentifiedImageError
from transformers import AutoImageProcessor, AutoModelForImageClassification

from aeris.logging import configure_logging as configure_aeris_logging


LOGGER = logging.getLogger("climate_pipeline")

CURRENT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT_DIR = CURRENT_DIR / "datasets" / "historical_eval"
DEFAULT_OUTPUT_FILE = CURRENT_DIR / "climate_multimodal_dataset.csv"

MODEL_A_ID = "mrm8488/convnext-tiny-finetuned-eurosat"
MODEL_B_ID = "prithivMLmods/Weather-Image-Classification"

OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
SANTOS_LATITUDE = -23.9618
SANTOS_LONGITUDE = -46.3322
SANTOS_TIMEZONE = "America/Sao_Paulo"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
TIMESTAMP_PATTERN = re.compile(r"(?P<date>\d{4}-\d{2}-\d{2})_(?P<hour>\d{2})-(?P<minute>\d{2})")

HOURLY_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "precipitation",
    "surface_pressure",
    "cloud_cover",
    "cloud_cover_low",
    "cloud_cover_mid",
    "cloud_cover_high",
    "shortwave_radiation",
    "direct_radiation",
    "diffuse_radiation",
    "wind_speed_10m",
    "wind_gusts_10m",
]

BASE_COLUMNS = [
    "arquivo_imagem",
    "timestamp_imagem",
    "timestamp_meteorologico",
    "latitude",
    "longitude",
    "classe_satelite",
    "confianca_satelite",
    "classe_perspectiva",
    "confianca_perspectiva",
]
OUTPUT_COLUMNS = BASE_COLUMNS + HOURLY_VARIABLES


@dataclass(slots=True)
class VisionModelBundle:
    """Container for a Hugging Face image classifier and its processor."""

    model_id: str
    processor: AutoImageProcessor
    model: AutoModelForImageClassification
    device: torch.device
    processor_fast: bool


@dataclass(frozen=True, slots=True)
class VisionPrediction:
    """Top-1 image classification result."""

    label: str
    confidence: float


@dataclass(frozen=True, slots=True)
class ClimatePipelineOptions:
    input_dir: Path = DEFAULT_INPUT_DIR
    output_file: Path = DEFAULT_OUTPUT_FILE
    device: str = "auto"
    api_timeout: float = 30.0
    sleep_seconds: float = 2.0
    max_images: int | None = None
    progress_callback: Callable[[str], None] | None = None


@dataclass(frozen=True, slots=True)
class ClimatePipelineSummary:
    attempted: int
    rows: int
    failed: int
    output_file: str
    errors: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera um dataset tabular multimodal com inferencias de imagem e dados Open-Meteo.",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help=f"Diretorio com imagens historicas. Padrao: {DEFAULT_INPUT_DIR}",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=DEFAULT_OUTPUT_FILE,
        help=f"CSV de saida. Padrao: {DEFAULT_OUTPUT_FILE}",
    )
    parser.add_argument(
        "--device",
        choices=("auto", "cuda", "cpu"),
        default="auto",
        help="Dispositivo para inferencia dos modelos. 'auto' usa CUDA se disponivel.",
    )
    parser.add_argument(
        "--api-timeout",
        type=float,
        default=30.0,
        help="Timeout, em segundos, para cada chamada Open-Meteo.",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=2.0,
        help="Pausa entre chamadas Open-Meteo para reduzir risco de rate-limit. Deve ser >= 1.0 para 10k+ imagens.",
    )
    parser.add_argument(
        "--max-images",
        type=int,
        default=None,
        help="Limite opcional de imagens para testes. Por padrao processa todas.",
    )
    return parser.parse_args()


def configure_logging() -> None:
    configure_aeris_logging("INFO")


def report_progress(callback: Callable[[str], None] | None, message: str) -> None:
    LOGGER.info(message)
    if callback is not None:
        callback(message)


def select_device(preference: str) -> torch.device:
    if preference == "cuda":
        if torch.cuda.is_available():
            return torch.device("cuda")
        LOGGER.warning("CUDA solicitado, mas nao esta disponivel. Usando CPU.")
        return torch.device("cpu")

    if preference == "cpu":
        return torch.device("cpu")

    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def load_classifier(model_id: str, device: torch.device) -> VisionModelBundle:
    LOGGER.info("Carregando modelo Hugging Face: %s", model_id)
    processor = AutoImageProcessor.from_pretrained(model_id, use_fast=True)
    model = AutoModelForImageClassification.from_pretrained(model_id)
    model.to(device)
    model.eval()
    return VisionModelBundle(model_id=model_id, processor=processor, model=model, device=device, processor_fast=True)


def iter_image_files(input_dir: Path) -> list[Path]:
    if not input_dir.exists():
        raise FileNotFoundError(f"Diretorio de entrada nao encontrado: {input_dir}")

    return sorted(
        path
        for path in input_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def parse_timestamp_from_filename(image_path: Path) -> datetime:
    match = TIMESTAMP_PATTERN.search(image_path.stem)
    if match is None:
        raise ValueError(
            f"Nome do arquivo nao contem timestamp no formato YYYY-MM-DD_HH-MM: {image_path.name}",
        )

    raw_timestamp = f"{match.group('date')}_{match.group('hour')}-{match.group('minute')}"
    return datetime.strptime(raw_timestamp, "%Y-%m-%d_%H-%M")


def normalize_to_hour(timestamp: datetime) -> datetime:
    """Open-Meteo Historical API returns hourly slots; minutes are rounded down."""

    if timestamp.minute != 0:
        LOGGER.warning(
            "Timestamp %s tem minuto diferente de 00; usando a hora %02d:00 para matching meteorologico.",
            timestamp.isoformat(timespec="minutes"),
            timestamp.hour,
        )
    return timestamp.replace(minute=0, second=0, microsecond=0)


def load_rgb_image(image_path: Path) -> Image.Image:
    try:
        with Image.open(image_path) as image:
            return image.convert("RGB")
    except UnidentifiedImageError as exc:
        raise ValueError(f"Imagem corrompida ou formato invalido: {image_path}") from exc


def tensor_inputs_to_device(inputs: dict[str, torch.Tensor], device: torch.device) -> dict[str, torch.Tensor]:
    return {key: value.to(device) for key, value in inputs.items()}


def label_from_config(model: AutoModelForImageClassification, class_index: int) -> str:
    id2label = getattr(model.config, "id2label", {}) or {}
    return id2label.get(class_index) or id2label.get(str(class_index)) or f"class_{class_index}"


def _predict_image_once(bundle: VisionModelBundle, image: Image.Image) -> VisionPrediction:
    inputs = bundle.processor(images=image, return_tensors="pt")
    inputs = tensor_inputs_to_device(dict(inputs), bundle.device)

    with torch.no_grad():
        logits = bundle.model(**inputs).logits
        probabilities = torch.softmax(logits, dim=-1)[0]
        confidence, class_index = torch.max(probabilities, dim=0)

    class_id = int(class_index.detach().cpu().item())
    label = label_from_config(bundle.model, class_id)
    return VisionPrediction(label=label, confidence=float(confidence.detach().cpu().item()))


def can_retry_with_slow_processor(exc: Exception) -> bool:
    message = str(exc)
    return "unsupported operand type(s)" in message or "NoneType" in message


def predict_image(bundle: VisionModelBundle, image: Image.Image) -> VisionPrediction:
    try:
        return _predict_image_once(bundle, image)
    except Exception as exc:
        if not bundle.processor_fast or not can_retry_with_slow_processor(exc):
            raise

        LOGGER.warning(
            "Processor rapido falhou para %s (%s). Recarregando com use_fast=False.",
            bundle.model_id,
            exc,
        )
        bundle.processor = AutoImageProcessor.from_pretrained(bundle.model_id, use_fast=False)
        bundle.processor_fast = False
        return _predict_image_once(bundle, image)


def find_hour_index(times: list[str], target_hour: datetime) -> int:
    for index, raw_time in enumerate(times):
        try:
            candidate = datetime.fromisoformat(raw_time).replace(tzinfo=None)
        except ValueError:
            continue

        if candidate == target_hour:
            return index

    raise ValueError(f"Horario {target_hour.isoformat(timespec='minutes')} nao encontrado na resposta Open-Meteo.")


def value_at_hour(hourly_payload: dict[str, Any], variable: str, hour_index: int) -> Any:
    values = hourly_payload.get(variable)
    if not isinstance(values, list):
        raise ValueError(f"Variavel ausente ou invalida na resposta Open-Meteo: {variable}")

    try:
        return values[hour_index]
    except IndexError as exc:
        raise ValueError(f"Variavel {variable} nao possui indice horario {hour_index}.") from exc


def fetch_weather_for_hour(timestamp: datetime, timeout: float, sleep_seconds: float) -> dict[str, Any]:
    target_hour = normalize_to_hour(timestamp)
    target_date = target_hour.date().isoformat()
    params = {
        "latitude": SANTOS_LATITUDE,
        "longitude": SANTOS_LONGITUDE,
        "start_date": target_date,
        "end_date": target_date,
        "hourly": ",".join(HOURLY_VARIABLES),
        "timezone": SANTOS_TIMEZONE,
    }

    max_retries = 3
    retry_delay = 2.0
    
    for attempt in range(max_retries):
        try:
            response = requests.get(OPEN_METEO_ARCHIVE_URL, params=params, timeout=timeout)
            response.raise_for_status()
            payload = response.json()
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)
                LOGGER.warning(
                    "Timeout na Open-Meteo para %s. Tentando novamente em %.1f segundos (tentativa %d/%d).",
                    target_date,
                    wait_time,
                    attempt + 1,
                    max_retries,
                )
                time.sleep(wait_time)
                continue
            raise
        except requests.exceptions.RequestException as exc:
            if attempt < max_retries - 1 and "429" in str(exc):
                wait_time = retry_delay * (2 ** attempt)
                LOGGER.warning(
                    "Rate limit detectado. Aguardando %.1f segundos (tentativa %d/%d).",
                    wait_time,
                    attempt + 1,
                    max_retries,
                )
                time.sleep(wait_time)
                continue
            raise
        finally:
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)

        hourly_payload = payload.get("hourly")
        if not isinstance(hourly_payload, dict):
            raise ValueError("Resposta Open-Meteo nao contem bloco 'hourly'.")

        times = hourly_payload.get("time")
        if not isinstance(times, list):
            raise ValueError("Resposta Open-Meteo nao contem lista 'hourly.time'.")

        hour_index = find_hour_index(times, target_hour)
        return {variable: value_at_hour(hourly_payload, variable, hour_index) for variable in HOURLY_VARIABLES}

    raise RuntimeError(f"Falha ao obter dados meteorologicos apos {max_retries} tentativas.")


def build_dataset_row(
    image_path: Path,
    timestamp: datetime,
    satellite_prediction: VisionPrediction,
    perspective_prediction: VisionPrediction,
    weather_data: dict[str, Any],
) -> dict[str, Any]:
    target_hour = normalize_to_hour(timestamp)
    row: dict[str, Any] = {
        "arquivo_imagem": str(image_path),
        "timestamp_imagem": timestamp.isoformat(timespec="minutes"),
        "timestamp_meteorologico": target_hour.isoformat(timespec="minutes"),
        "latitude": SANTOS_LATITUDE,
        "longitude": SANTOS_LONGITUDE,
        "classe_satelite": satellite_prediction.label,
        "confianca_satelite": satellite_prediction.confidence,
        "classe_perspectiva": perspective_prediction.label,
        "confianca_perspectiva": perspective_prediction.confidence,
    }
    row.update(weather_data)
    return row


def process_image(
    image_path: Path,
    satellite_model: VisionModelBundle,
    perspective_model: VisionModelBundle,
    api_timeout: float,
    sleep_seconds: float,
) -> dict[str, Any]:
    timestamp = parse_timestamp_from_filename(image_path)
    image = load_rgb_image(image_path)

    satellite_prediction = predict_image(satellite_model, image)
    perspective_prediction = predict_image(perspective_model, image)
    weather_data = fetch_weather_for_hour(timestamp, timeout=api_timeout, sleep_seconds=sleep_seconds)

    return build_dataset_row(
        image_path=image_path,
        timestamp=timestamp,
        satellite_prediction=satellite_prediction,
        perspective_prediction=perspective_prediction,
        weather_data=weather_data,
    )


def run_climate_pipeline(options: ClimatePipelineOptions) -> ClimatePipelineSummary:
    device = select_device(options.device)
    report_progress(options.progress_callback, f"Usando dispositivo para inferencia: {device}")

    report_progress(options.progress_callback, f"Carregando modelo satelite: {MODEL_A_ID}")
    satellite_model = load_classifier(MODEL_A_ID, device)
    report_progress(options.progress_callback, f"Carregando modelo perspectiva: {MODEL_B_ID}")
    perspective_model = load_classifier(MODEL_B_ID, device)

    image_files = iter_image_files(options.input_dir)
    if options.max_images is not None:
        image_files = image_files[: options.max_images]
    report_progress(options.progress_callback, f"Imagens selecionadas: {len(image_files)}")

    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    failed = 0
    for index, image_path in enumerate(image_files, start=1):
        report_progress(options.progress_callback, f"Processando {index}/{len(image_files)}: {image_path.name}")
        try:
            row = process_image(
                image_path=image_path,
                satellite_model=satellite_model,
                perspective_model=perspective_model,
                api_timeout=options.api_timeout,
                sleep_seconds=options.sleep_seconds,
            )
        except Exception as exc:
            failed += 1
            errors.append(f"{image_path.name}: {exc}")
            LOGGER.exception("Falha ao processar %s. Pulando para a proxima imagem.", image_path)
            continue

        rows.append(row)

    output_file = options.output_file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    dataframe = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    dataframe.to_csv(output_file, index=False, encoding="utf-8")

    LOGGER.info("Dataset salvo em %s com %d linhas.", output_file, len(dataframe))
    return ClimatePipelineSummary(
        attempted=len(image_files),
        rows=len(dataframe),
        failed=failed,
        output_file=str(output_file),
        errors=errors,
    )


def main() -> None:
    configure_logging()
    args = parse_args()

    run_climate_pipeline(
        ClimatePipelineOptions(
            input_dir=args.input_dir,
            output_file=args.output_file,
            device=args.device,
            api_timeout=args.api_timeout,
            sleep_seconds=args.sleep_seconds,
            max_images=args.max_images,
        ),
    )


if __name__ == "__main__":
    main()
