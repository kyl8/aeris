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
DEFAULT_WEATHER_MODEL_ID = "aeris-weather-classifier-v1"
DEFAULT_WEATHER_MODEL_DIRNAME = "aeris-weather-siglip2"
DEFAULT_CLASS_LABELS = (
    "cloudy/overcast",
    "foggy/hazy",
    "rain/storm",
    "snow/frosty",
    "sun/clear",
)
DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
ALLOWED_ORIGINS = DEFAULT_ALLOWED_ORIGINS
PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEIGHTS_DIR = PROJECT_ROOT / "weights"
WEIGHTS_EXTENSIONS = {
    ".ckpt",
    ".h5",
    ".joblib",
    ".keras",
    ".onnx",
    ".pkl",
    ".pickle",
    ".safetensors",
    ".pt",
    ".pth",
}


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
    image_size: int
    class_labels: tuple[str, ...]


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
        image_size=image_size,
        class_labels=class_labels,
    )
