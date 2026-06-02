from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import io
import logging
from time import perf_counter

from .config import APP_VERSION, DEFAULT_CLASS_LABELS, DEFAULT_MODEL_NAME, get_settings
from .preprocessing import build_heatmap_base64, extract_image_profile, validate_image_bytes

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PredictionOutcome:
    prediction_class: str
    confidence: float
    heatmap: str | None
    model_name: str
    model_version: str
    source: str
    inference_ms: float
    top_predictions: list[dict[str, float | str]]
    image_profile: dict[str, float]
    explanation: list[str]
    risk_flags: list[str]


class AerisPredictor:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._labels = self._resolve_labels()

        self._transformers_model = None
        self._transformers_processor = None
        self._transformers_model_name = None
        try:
            from .model import load_weather_transformers_model

            weather_bundle = load_weather_transformers_model(self._labels)
            if weather_bundle is not None:
                self._transformers_model = weather_bundle.model
                self._transformers_processor = weather_bundle.processor
                self._transformers_model_name = weather_bundle.name
                logger.info("weather_transformers_model_loaded", extra={"model_name": self._transformers_model_name})
        except Exception:
            logger.exception("weather_model_load_failed")

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

    def predict(self, *, image_bytes: bytes) -> PredictionOutcome:
        validate_image_bytes(image_bytes)
        start_time = perf_counter()
        profile = extract_image_profile(image_bytes)

        if self._transformers_model is not None and self._transformers_processor is not None:
            prediction_class, confidence, source, top_predictions = self._predict_with_transformers(image_bytes)
        else:
            prediction_class, confidence, source, top_predictions = self._predict_with_heuristics(profile)

        heatmap = build_heatmap_base64(image_bytes)
        inference_ms = round((perf_counter() - start_time) * 1000, 2)

        model_name = self._transformers_model_name if self._transformers_model is not None else DEFAULT_MODEL_NAME
        explanation = self._build_explanation(profile, prediction_class, source)
        risk_flags = self._build_risk_flags(profile, confidence, source, top_predictions)

        return PredictionOutcome(
            prediction_class=prediction_class,
            confidence=confidence,
            heatmap=heatmap,
            model_name=model_name,
            model_version=APP_VERSION,
            source=source,
            inference_ms=inference_ms,
            top_predictions=top_predictions,
            image_profile=profile,
            explanation=explanation,
            risk_flags=risk_flags,
        )

    def _predict_with_transformers(self, image_bytes: bytes) -> tuple[str, float, str, list[dict[str, float | str]]]:
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

        top_count = min(5, probabilities.shape[0])
        top_scores, top_indexes = torch.topk(probabilities, k=top_count)
        top_predictions = [
            {
                "label": self._label_for_index(int(index.item())),
                "confidence": round(float(score.item()), 4),
            }
            for score, index in zip(top_scores, top_indexes)
        ]

        best_prediction = top_predictions[0]
        return str(best_prediction["label"]), float(best_prediction["confidence"]), "transformers", top_predictions

    def _label_for_index(self, index: int) -> str:
        return self._labels[index] if index < len(self._labels) else f"class_{index}"

    def _predict_with_heuristics(self, profile: dict[str, float]) -> tuple[str, float, str, list[dict[str, float | str]]]:
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
        top_predictions = [
            {"label": label, "confidence": round(max(score, 0.0) / total_score, 4)}
            for label, score in sorted(scores.items(), key=lambda item: item[1], reverse=True)
        ]
        confidence = float(top_predictions[0]["confidence"])

        return best_label, confidence, "heuristic", top_predictions

    def _build_explanation(self, profile: dict[str, float], prediction_class: str, source: str) -> list[str]:
        explanation = [
            f"Fonte da inferência: {source}.",
            f"Classe dominante: {prediction_class}.",
        ]

        if profile["brightness"] >= 170:
            explanation.append("Brilho alto favorece cenas claras, neve/geada ou céu aberto.")
        elif profile["brightness"] <= 95:
            explanation.append("Baixo brilho aumenta o peso de chuva, tempestade ou cena escura.")

        if profile["saturation"] <= 80:
            explanation.append("Baixa saturação favorece neblina, nublado e condições homogêneas.")
        elif profile["saturation"] >= 160:
            explanation.append("Saturação elevada indica cena visualmente mais definida.")

        if profile["contrast"] >= 75 or profile["edge_strength"] >= 180:
            explanation.append("Contraste e transições fortes indicam textura visual relevante no frame.")

        return explanation

    def _build_risk_flags(
        self,
        profile: dict[str, float],
        confidence: float,
        source: str,
        top_predictions: list[dict[str, float | str]],
    ) -> list[str]:
        flags: list[str] = []

        if source == "heuristic":
            flags.append("Modelo neural indisponível: usando fallback heurístico local.")

        if confidence < 0.45:
            flags.append("Confiança baixa: classes próximas, trate como triagem visual.")

        if len(top_predictions) > 1:
            margin = float(top_predictions[0]["confidence"]) - float(top_predictions[1]["confidence"])
            if margin < 0.12:
                flags.append("Margem pequena entre as duas classes mais prováveis.")

        if profile["brightness"] < 35 or profile["brightness"] > 235:
            flags.append("Frame com exposição extrema pode reduzir a confiabilidade.")

        return flags



@lru_cache(maxsize=1)
def get_predictor() -> AerisPredictor:
    return AerisPredictor()
