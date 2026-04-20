from dataclasses import dataclass
from pathlib import Path

from .config import DEFAULT_MODEL_NAME, APP_VERSION, WEIGHTS_DIR, WEIGHTS_EXTENSIONS


@dataclass(slots=True)
class ModelArtifact:
    name: str
    version: str
    path: Path | None


def discover_model_artifact() -> ModelArtifact:
    if not WEIGHTS_DIR.exists():
        return ModelArtifact(name=DEFAULT_MODEL_NAME, version=APP_VERSION, path=None)

    candidates = [
        path
        for path in WEIGHTS_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in WEIGHTS_EXTENSIONS
    ]

    if not candidates:
        return ModelArtifact(name=DEFAULT_MODEL_NAME, version=APP_VERSION, path=None)

    latest_artifact = max(candidates, key=lambda candidate: candidate.stat().st_mtime)
    return ModelArtifact(
        name=latest_artifact.stem,
        version=APP_VERSION,
        path=latest_artifact,
    )