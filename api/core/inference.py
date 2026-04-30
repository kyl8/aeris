from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import io
import logging
from time import perf_counter
from typing import Sequence

from .config import DEFAULT_CLASS_LABELS, DEFAULT_MODEL_NAME, get_settings
from .model import discover_model_artifact
from .preprocessing import build_heatmap_base64, extract_image_profile, validate_image_bytes

logger = logging.getLogger(__name__)

try:  
    import numpy as np
except Exception:  # pragma: no cover - fallback when numpy is unavailable
    np = None

try:  
    import onnxruntime as ort
except Exception:  
    ort = None


@dataclass(slots=True)
class PredictionOutcome:
    prediction_class: str
    confidence: float
    heatmap: str | None
    model_name: str
    model_version: str
    source: str
    inference_ms: float


class AerisPredictor:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._artifact = discover_model_artifact()
        self._labels = self._resolve_labels()
        self._session = None
        self._input_name = None
        self._input_channels = 3
        self._input_layout = "NCHW"
        self._input_size = self._settings.image_size

        self._transformers_model = None
        self._transformers_processor = None
        self._transformers_model_name = None
        self._pytorch_model = None
        try:
            from .model import load_or_create_pytorch_model, load_weather_transformers_model

            weather_bundle = load_weather_transformers_model(self._labels)
            if weather_bundle is not None:
                self._transformers_model = weather_bundle.model
                self._transformers_processor = weather_bundle.processor
                self._transformers_model_name = weather_bundle.name
                logger.info("weather_transformers_model_loaded", extra={"model_name": self._transformers_model_name})
            else:
                self._pytorch_model = load_or_create_pytorch_model(len(self._labels))
                if self._pytorch_model is not None:
                    logger.info("pytorch_model_loaded")
        except Exception:
            logger.exception("weather_model_load_failed")

        if self._artifact.path is not None and ort is not None and np is not None:
            try:
                session_options = ort.SessionOptions()
                session_options.intra_op_num_threads = 1
                session_options.inter_op_num_threads = 1
                session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

                self._session = ort.InferenceSession(
                    str(self._artifact.path),
                    sess_options=session_options,
                    providers=["CPUExecutionProvider"],
                )
                self._configure_session_metadata()
                logger.info(
                    "onnx_model_loaded",
                    extra={"model_name": self._artifact.name, "model_path": str(self._artifact.path)},
                )
            except Exception:  
                logger.exception("onnx_model_load_failed")
                self._session = None

    def _resolve_labels(self) -> list[str]:
        import json
        classes_path = self._settings.weights_dir / "aeris-classes.json"
        if classes_path.exists():
            try:
                with open(classes_path, "r", encoding="utf-8") as f:
                    labels = json.load(f)
                if isinstance(labels, list) and len(labels) > 0:
                    return labels
            except Exception:
                logger.warning("Failed to load aeris-classes.json, falling back to defaults.")
        
        labels = list(self._settings.class_labels)
        return labels if labels else list(DEFAULT_CLASS_LABELS)

    def _configure_session_metadata(self) -> None:
        if self._session is None:
            return

        input_metadata = self._session.get_inputs()[0]
        shape = input_metadata.shape or []

        if len(shape) >= 4:
            if isinstance(shape[1], int) and shape[1] in {1, 3}:
                self._input_channels = shape[1]
                self._input_layout = "NCHW"
                height = shape[2]
                width = shape[3]
            elif isinstance(shape[-1], int) and shape[-1] in {1, 3}:
                self._input_channels = shape[-1]
                self._input_layout = "NHWC"
                height = shape[1]
                width = shape[2]
            else:
                height = shape[2]
                width = shape[3]

            if isinstance(height, int) and height > 0:
                self._input_size = height
            if isinstance(width, int) and width > 0:
                self._input_size = min(self._input_size, width)

        self._input_name = input_metadata.name

    def predict(self, *, image_bytes: bytes) -> PredictionOutcome:
        validate_image_bytes(image_bytes)
        start_time = perf_counter()

        if self._transformers_model is not None and self._transformers_processor is not None:
            prediction_class, confidence, source = self._predict_with_transformers(image_bytes)
        elif self._pytorch_model is not None:
            prediction_class, confidence, source = self._predict_with_pytorch(image_bytes)
        elif self._session is not None:
            prediction_class, confidence, source = self._predict_with_onnx(image_bytes)
        else:
            prediction_class, confidence, source = self._predict_with_heuristics(image_bytes)

        heatmap = build_heatmap_base64(image_bytes)
        inference_ms = round((perf_counter() - start_time) * 1000, 2)

        model_name = (
            self._transformers_model_name
            if self._transformers_model is not None
            else (
                "aeris-resnet18"
                if self._pytorch_model is not None
                else (self._artifact.name if self._artifact.path else DEFAULT_MODEL_NAME)
            )
        )

        return PredictionOutcome(
            prediction_class=prediction_class,
            confidence=confidence,
            heatmap=heatmap,
            model_name=model_name,
            model_version=self._artifact.version,
            source=source,
            inference_ms=inference_ms,
        )

    def _predict_with_transformers(self, image_bytes: bytes) -> tuple[str, float, str]:
        import torch
        from PIL import Image

        if self._transformers_model is None or self._transformers_processor is None:
            raise RuntimeError("O modelo SigLIP não foi inicializado.")

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        inputs = self._transformers_processor(images=image, return_tensors="pt")
        device = next(self._transformers_model.parameters()).device
        inputs = {key: value.to(device) for key, value in inputs.items()}

        with torch.inference_mode():
            outputs = self._transformers_model(**inputs)
            probabilities = torch.softmax(outputs.logits[0], dim=0)

        best_score, best_index = torch.max(probabilities, dim=0)
        best_index = int(best_index.item())
        best_score = float(best_score.item())

        label = self._labels[best_index] if best_index < len(self._labels) else f"class_{best_index}"
        return label, round(best_score, 4), "transformers"

    def _predict_with_pytorch(self, image_bytes: bytes) -> tuple[str, float, str]:
        import torch
        from .preprocessing import transform_image_for_pytorch
        
        tensor = transform_image_for_pytorch(image_bytes)
        with torch.no_grad():
            outputs = self._pytorch_model(tensor)
            probabilities = torch.nn.functional.softmax(outputs[0], dim=0)
            
        best_score, best_index = torch.max(probabilities, dim=0)
        best_index = int(best_index.item())
        best_score = float(best_score.item())
        
        label = self._labels[best_index] if best_index < len(self._labels) else f"class_{best_index}"
        return label, round(best_score, 4), "pytorch"

    def _predict_with_onnx(self, image_bytes: bytes) -> tuple[str, float, str]:
        if self._session is None or self._input_name is None or np is None:
            raise RuntimeError("A sessão ONNX não foi inicializada.")

        tensor = self._build_tensor_from_bytes(image_bytes)
        outputs = self._session.run(None, {self._input_name: tensor})
        scores = self._extract_scores(outputs)
        probabilities = self._scores_to_probabilities(scores)

        best_index = int(np.argmax(probabilities))
        best_score = float(probabilities[best_index])
        label = self._labels[best_index] if best_index < len(self._labels) else f"class_{best_index}"

        return label, round(best_score, 4), "onnx"

    def _predict_with_heuristics(self, image_bytes: bytes) -> tuple[str, float, str]:
        profile = extract_image_profile(image_bytes)
        scores = {
            "cloudy/overcast": (255.0 - profile["saturation"]) * 0.18
            + (220.0 - abs(profile["brightness"] - 155.0)) * 0.18,
            "foggy/hazy": (255.0 - profile["contrast"]) * 0.24
            + (255.0 - profile["saturation"]) * 0.22
            + (255.0 - profile["brightness"]) * 0.08,
            "rain/storm": (255.0 - profile["brightness"]) * 0.22
            + profile["edge_strength"] * 0.22
            + profile["blue"] * 0.05
            + profile["contrast"] * 0.12,
            "snow/frosty": profile["brightness"] * 0.22
            + (255.0 - profile["saturation"]) * 0.18
            + (255.0 - profile["contrast"]) * 0.08,
            "sun/clear": profile["brightness"] * 0.42 + profile["saturation"] * 0.08 - profile["contrast"] * 0.05,
        }

        best_label = max(scores, key=scores.get)
        total_score = sum(max(value, 0.0) for value in scores.values()) or 1.0
        confidence = scores[best_label] / total_score
        confidence = round(min(max(confidence, 0.58), 0.97), 4)

        return best_label, confidence, "heuristic"

    def _extract_scores(self, outputs: Sequence[object]) -> np.ndarray:
        if not outputs:
            raise RuntimeError("O modelo ONNX não retornou saídas.")

        raw_scores = np.asarray(outputs[0], dtype=np.float32)
        if raw_scores.ndim == 0:
            raw_scores = raw_scores.reshape(1)

        if raw_scores.ndim > 1:
            raw_scores = raw_scores[0]

        return raw_scores.astype(np.float32)

    def _scores_to_probabilities(self, scores: np.ndarray) -> np.ndarray:
        if scores.size == 0:
            return np.array([1.0], dtype=np.float32)

        if np.all(scores >= 0.0) and np.all(scores <= 1.0):
            total = float(scores.sum())
            if 0.99 <= total <= 1.01:
                return scores

        clipped_scores = scores - float(np.max(scores))
        exponentials = np.exp(clipped_scores)
        total = float(exponentials.sum()) or 1.0
        return exponentials / total

    def _build_tensor_from_bytes(self, image_bytes: bytes) -> np.ndarray:
        if np is None:
            raise RuntimeError("NumPy é necessário para executar um modelo ONNX.")

        source = np.frombuffer(image_bytes, dtype=np.uint8)
        if source.size == 0:
            raise ValueError("A imagem enviada está vazia.")

        total_values = self._input_size * self._input_size * self._input_channels
        tiled = np.resize(source, total_values).astype(np.float32) / 255.0

        if self._input_channels == 1:
            if self._input_layout == "NHWC":
                return tiled.reshape(1, self._input_size, self._input_size, 1)

            return tiled.reshape(1, 1, self._input_size, self._input_size)

        if self._input_layout == "NHWC":
            return tiled.reshape(1, self._input_size, self._input_size, self._input_channels)

        return tiled.reshape(1, self._input_size, self._input_size, self._input_channels).transpose(0, 3, 1, 2)


@lru_cache(maxsize=1)
def get_predictor() -> AerisPredictor:
    return AerisPredictor()
