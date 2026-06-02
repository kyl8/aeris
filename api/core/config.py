from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from tempfile import gettempdir
import os

APP_NAME = "Aeris API"
APP_VERSION = "0.1.0"
APP_DESCRIPTION = "API de análise climática com inferência por imagem, histórico e documentação interativa."
API_PREFIX = "/api"
API_V1_PREFIX = "/api/v1"
DEFAULT_MODEL_NAME = "aeris-weather-classifier"
DEFAULT_WEATHER_MODEL_ID = "prithivMLmods/Weather-Image-Classification"
DEFAULT_WEATHER_MODEL_DIRNAME = "aeris-weather-siglip2"
DEFAULT_WEATHER_MODEL_METADATA = "aeris-training-metadata.json"
DEFAULT_CLASS_LABELS = (
    "cloudy/overcast",
    "foggy/hazy",
    "rain/storm",
    "snow/frosty",
    "sun/clear",
)
DEFAULT_DETECTION_MODEL_ID = "google/owlvit-base-patch32"
DEFAULT_DETECTION_LABELS = (
    "a person", "a bicycle", "a car", "a motorcycle", "an airplane", "a bus",
    "a train", "a truck", "a boat", "a traffic light", "a fire hydrant",
    "a stop sign", "a parking meter", "a bench", "a bird", "a cat", "a dog",
    "a horse", "a sheep", "a cow", "an elephant", "a bear", "a zebra",
    "a giraffe", "a backpack", "an umbrella", "a handbag", "a tie", "a suitcase",
    "a frisbee", "skis", "a snowboard", "a sports ball", "a kite",
    "a baseball bat", "a baseball glove", "a skateboard", "a surfboard",
    "a tennis racket", "a bottle", "a wine glass", "a cup", "a fork", "a knife",
    "a spoon", "a bowl", "a banana", "an apple", "a sandwich", "an orange",
    "broccoli", "a carrot", "a hot dog", "a pizza", "a donut", "a cake",
    "a chair", "a couch", "a potted plant", "a bed", "a dining table",
    "a toilet", "a tv", "a laptop", "a mouse", "a remote", "a keyboard",
    "a cell phone", "a microwave", "an oven", "a toaster", "a sink",
    "a refrigerator", "a book", "a clock", "a vase", "scissors",
    "a teddy bear", "a hair drier", "a toothbrush",
)
DEFAULT_DETECTION_THRESHOLD = 0.12
DEFAULT_DETECTION_MAX_RESULTS = 15
DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
ALLOWED_ORIGINS = DEFAULT_ALLOWED_ORIGINS
PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPOSITORY_ROOT = PROJECT_ROOT.parent
WEIGHTS_DIR = PROJECT_ROOT / "weights"
HF_CACHE_DIR = PROJECT_ROOT / "weights" / "hf_cache"
os.environ.setdefault("HF_HOME", str(HF_CACHE_DIR))
os.environ.setdefault("OMP_NUM_THREADS", str(max(1, (os.cpu_count() or 4) // 2)))
HISTORICAL_EVAL_DIR = PROJECT_ROOT / "datasets" / "historical_eval"
CLIMATE_DATASET_PATH = PROJECT_ROOT / "climate_multimodal_dataset.csv"


@dataclass(slots=True)
class Settings:
    environment: str
    debug: bool
    app_name: str
    app_version: str
    app_description: str
    api_prefix: str
    api_v1_prefix: str
    allowed_origins: list[str]
    log_level: str
    weights_dir: Path
    model_path: Path | None
    history_db_path: Path
    historical_eval_dir: Path
    climate_dataset_path: Path
    image_size: int
    class_labels: tuple[str, ...]
    weather_model_source: str
    detection_model_id: str
    detection_labels: tuple[str, ...]
    detection_threshold: float
    detection_max_results: int
    hf_cache_dir: Path


def _parse_bool(raw_value: str | None, default: bool = False) -> bool:
    if raw_value is None:
        return default

    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_csv(raw_value: str | None, default: list[str]) -> list[str]:
    if not raw_value:
        return default

    values = [item.strip() for item in raw_value.split(",")]
    return [item for item in values if item]


def _resolve_model_path(raw_value: str | None) -> Path | None:
    if not raw_value:
        return None

    candidate = Path(raw_value).expanduser()
    return candidate if candidate.exists() else None


def _default_history_path() -> Path:
    history_root = Path(gettempdir()) / "aeris"
    return history_root / f"history-{os.getpid()}.sqlite3"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    environment = os.getenv("AERIS_ENV", "development").strip().lower() or "development"
    debug = _parse_bool(os.getenv("AERIS_DEBUG"), default=environment != "production")
    allowed_origins = _parse_csv(os.getenv("AERIS_ALLOWED_ORIGINS"), DEFAULT_ALLOWED_ORIGINS)
    class_labels = tuple(
        label for label in _parse_csv(os.getenv("AERIS_CLASS_LABELS"), list(DEFAULT_CLASS_LABELS)) if label
    )
    image_size = int(os.getenv("AERIS_IMAGE_SIZE", "224"))

    return Settings(
        environment=environment,
        debug=debug,
        app_name=APP_NAME,
        app_version=APP_VERSION,
        app_description=APP_DESCRIPTION,
        api_prefix=API_PREFIX,
        api_v1_prefix=API_V1_PREFIX,
        allowed_origins=allowed_origins,
        log_level=os.getenv("AERIS_LOG_LEVEL", "INFO").strip().upper() or "INFO",
        weights_dir=Path(os.getenv("AERIS_WEIGHTS_DIR", str(WEIGHTS_DIR))).expanduser(),
        model_path=_resolve_model_path(os.getenv("AERIS_MODEL_PATH")),
        history_db_path=Path(os.getenv("AERIS_HISTORY_DB", str(_default_history_path()))).expanduser(),
        historical_eval_dir=Path(
            os.getenv("AERIS_HISTORICAL_EVAL_DIR", str(HISTORICAL_EVAL_DIR)),
        ).expanduser(),
        climate_dataset_path=Path(
            os.getenv("AERIS_CLIMATE_DATASET_PATH", str(CLIMATE_DATASET_PATH)),
        ).expanduser(),
        image_size=image_size,
        class_labels=class_labels,
        weather_model_source=os.getenv("AERIS_WEATHER_MODEL_SOURCE", "auto").strip().lower() or "auto",
        detection_model_id=os.getenv("AERIS_DETECTION_MODEL_ID", DEFAULT_DETECTION_MODEL_ID).strip()
        or DEFAULT_DETECTION_MODEL_ID,
        detection_labels=tuple(
            label
            for label in _parse_csv(os.getenv("AERIS_DETECTION_LABELS"), list(DEFAULT_DETECTION_LABELS))
            if label
        ),
        detection_threshold=float(os.getenv("AERIS_DETECTION_THRESHOLD", str(DEFAULT_DETECTION_THRESHOLD))),
        detection_max_results=int(os.getenv("AERIS_DETECTION_MAX_RESULTS", str(DEFAULT_DETECTION_MAX_RESULTS))),
        hf_cache_dir=Path(os.getenv("AERIS_HF_CACHE_DIR", str(HF_CACHE_DIR))).expanduser(),
    )
