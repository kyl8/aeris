from pathlib import Path

APP_NAME = "Aeris API"
APP_VERSION = "0.1.0"
APP_DESCRIPTION = "API de inferência do projeto Aeris construída com FastAPI."
API_PREFIX = "/api"
DEFAULT_MODEL_NAME = "baseline-placeholder"
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
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
    ".pt",
    ".pth",
}