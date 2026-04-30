from collections.abc import Sequence
from dataclasses import dataclass
import logging
from pathlib import Path

from .config import (
    APP_VERSION,
    DEFAULT_MODEL_NAME,
    DEFAULT_WEATHER_MODEL_ID,
    DEFAULT_WEATHER_MODEL_DIRNAME,
    WEIGHTS_EXTENSIONS,
    get_settings,
)


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ModelArtifact:
    name: str
    version: str
    path: Path | None


@dataclass(slots=True)
class WeatherModelBundle:
    model: object
    processor: object
    name: str


def discover_model_artifact() -> ModelArtifact:
    settings = get_settings()

    if settings.model_path is not None:
        return ModelArtifact(name=settings.model_path.stem, version=APP_VERSION, path=settings.model_path)

    if not settings.weights_dir.exists():
        return ModelArtifact(name=DEFAULT_MODEL_NAME, version=APP_VERSION, path=None)

    candidates = [
        path
        for path in settings.weights_dir.rglob("*")
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

def load_or_create_pytorch_model(num_classes: int = 5):
    try:
        import torch
        from torchvision.models import resnet18, ResNet18_Weights
    except ImportError:
        logger.warning("Pytorch não instalado. Não é possível carregar ou criar o modelo ResNet18.")
        return None

    settings = get_settings()
    weights_path = settings.weights_dir / f"{DEFAULT_MODEL_NAME}.pt"
    model = resnet18(weights=ResNet18_Weights.DEFAULT)
    model.fc = torch.nn.Linear(model.fc.in_features, num_classes)
    
    if weights_path.exists():
        logger.info(f"Carregando de {weights_path}")
        try:
            model.load_state_dict(torch.load(weights_path, map_location="cpu", weights_only=True))
        except Exception as e:
            logger.error(f"Falha ao carregar: {e}")
    else:
        logger.info(f"Sem modelos em {weights_path}. Salvando modelo inicial em {weights_path}")
        settings.weights_dir.mkdir(parents=True, exist_ok=True)
        torch.save(model.state_dict(), weights_path)
    
    model.eval()
    return model


def load_weather_transformers_model(class_labels: Sequence[str]) -> WeatherModelBundle | None:
    try:
        from transformers import AutoImageProcessor, SiglipForImageClassification
    except ImportError:
        logger.warning("Transformers não instalado. Não é possível carregar o modelo SigLIP para classificação climática.")
        return None

    settings = get_settings()
    model_dir = settings.weights_dir / DEFAULT_WEATHER_MODEL_DIRNAME
    model_source = model_dir if (model_dir / "config.json").exists() else DEFAULT_WEATHER_MODEL_ID

    labels = [label for label in class_labels if label]
    if not labels:
        logger.warning("Sem classes válidas para o modelo SigLIP. Verifique as configurações de class_labels.")
        return None

    try:
        processor = AutoImageProcessor.from_pretrained(model_source, use_fast=True)
        model = SiglipForImageClassification.from_pretrained(model_source)
        model.config.id2label = {index: label for index, label in enumerate(labels)}
        model.config.label2id = {label: index for index, label in enumerate(labels)}
        model.eval()
        model_name = model_dir.name if model_source == model_dir else DEFAULT_WEATHER_MODEL_ID
        return WeatherModelBundle(model=model, processor=processor, name=model_name)
    except Exception:
        logger.exception("Falha ao carregar o modelo SigLIP para classificação climática.")
        return None
