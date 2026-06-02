from collections.abc import Sequence
from dataclasses import dataclass
import logging
from pathlib import Path

from .config import (
    DEFAULT_WEATHER_MODEL_ID,
    DEFAULT_WEATHER_MODEL_DIRNAME,
    DEFAULT_WEATHER_MODEL_METADATA,
    get_settings,
)


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class WeatherModelBundle:
    model: object
    processor: object
    name: str


def load_weather_transformers_model(class_labels: Sequence[str]) -> WeatherModelBundle | None:
    try:
        from transformers import AutoImageProcessor, SiglipForImageClassification
    except ImportError:
        logger.warning("Transformers não instalado. Não é possível carregar o modelo SigLIP para classificação climática.")
        return None

    settings = get_settings()
    model_dir = settings.weights_dir / DEFAULT_WEATHER_MODEL_DIRNAME
    local_model_available = (model_dir / "config.json").exists()
    local_model_ready = (model_dir / DEFAULT_WEATHER_MODEL_METADATA).exists()

    explicit_remote = settings.weather_model_source in {"base", "hf", "huggingface", "remote"}

    if explicit_remote:
        model_source = DEFAULT_WEATHER_MODEL_ID
    elif settings.weather_model_source == "local":
        if not local_model_available:
            logger.warning("Modelo local solicitado, mas não encontrado em %s. Usando modelo base.", model_dir)
        model_source = model_dir if local_model_available else DEFAULT_WEATHER_MODEL_ID
    else:
        if settings.weather_model_source != "auto":
            logger.warning("AERIS_WEATHER_MODEL_SOURCE='%s' inválido. Usando auto.", settings.weather_model_source)
        if local_model_available and not local_model_ready:
            logger.warning(
                "Modelo local encontrado em %s, mas sem metadados do treino corrigido. "
                "Usando modelo base; defina AERIS_WEATHER_MODEL_SOURCE=local para forçar.",
                model_dir,
            )
        model_source = model_dir if local_model_available and local_model_ready else DEFAULT_WEATHER_MODEL_ID

    labels = [label for label in class_labels if label]
    if not labels:
        logger.warning("Sem classes válidas para o modelo SigLIP. Verifique as configurações de class_labels.")
        return None

    try:
        local_files_only = model_source != DEFAULT_WEATHER_MODEL_ID
        processor = AutoImageProcessor.from_pretrained(model_source, use_fast=True, local_files_only=local_files_only)
        model = SiglipForImageClassification.from_pretrained(model_source, local_files_only=local_files_only)
        model.config.id2label = {index: label for index, label in enumerate(labels)}
        model.config.label2id = {label: index for index, label in enumerate(labels)}
        model.eval()
        model_name = model_dir.name if model_source == model_dir else DEFAULT_WEATHER_MODEL_ID
        return WeatherModelBundle(model=model, processor=processor, name=model_name)
    except Exception:
        logger.exception("Falha ao carregar o modelo SigLIP para classificação climática.")
        return None
