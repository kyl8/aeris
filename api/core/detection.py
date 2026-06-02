from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import io
import logging
from time import perf_counter

from .config import get_settings
from .preprocessing import validate_image_bytes

logger = logging.getLogger(__name__)

_STOPWORDS = {"the", "a", "an"}


def _display_label(raw_label: str) -> str:
    words = [word for word in raw_label.split() if word.lower() not in _STOPWORDS]
    return " ".join(words) or raw_label


@dataclass(slots=True)
class Detection:
    label: str
    confidence: float
    box: dict[str, float]  # x, y, width, height as fractions [0, 1]


@dataclass(slots=True)
class DetectionOutcome:
    detections: list[Detection]
    model_name: str
    source: str
    inference_ms: float
    width: int
    height: int


class AerisDetector:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._labels = [label for label in self._settings.detection_labels if label]
        self._model = None
        self._processor = None
        try:
            import os
            import torch
            from transformers import OwlViTForObjectDetection, OwlViTProcessor

            threads = int(os.getenv("AERIS_TORCH_THREADS", str(max(1, (os.cpu_count() or 4) // 2))))
            torch.set_num_threads(threads)

            cache_dir = str(self._settings.hf_cache_dir)
            self._settings.hf_cache_dir.mkdir(parents=True, exist_ok=True)
            self._processor = OwlViTProcessor.from_pretrained(self._settings.detection_model_id, cache_dir=cache_dir)
            self._model = OwlViTForObjectDetection.from_pretrained(self._settings.detection_model_id, cache_dir=cache_dir)
            self._model.eval()
            logger.info("detection_model_loaded", extra={"model_name": self._settings.detection_model_id})
        except Exception:
            logger.exception("detection_model_load_failed")

    @property
    def available(self) -> bool:
        return self._model is not None and self._processor is not None and bool(self._labels)

    def detect(self, *, image_bytes: bytes) -> DetectionOutcome:
        validate_image_bytes(image_bytes)
        if not self.available:
            raise RuntimeError("O modelo de detecção OWL-ViT não está disponível.")

        import torch
        from PIL import Image

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        width, height = image.size

        start_time = perf_counter()
        inputs = self._processor(text=[self._labels], images=image, return_tensors="pt")
        with torch.inference_mode():
            outputs = self._model(**inputs)

        results = self._processor.post_process_grounded_object_detection(
            outputs=outputs,
            threshold=self._settings.detection_threshold,
            target_sizes=torch.tensor([[height, width]]),
            text_labels=[self._labels],
        )[0]

        from torchvision.ops import nms

        boxes_t = results["boxes"]
        scores_t = results["scores"]
        if boxes_t.numel():
            keep = nms(boxes_t, scores_t, iou_threshold=0.3)
            boxes_t = boxes_t[keep]
            scores_t = scores_t[keep]
            text_labels = [results["text_labels"][i] for i in keep.tolist()]
        else:
            text_labels = []
        inference_ms = round((perf_counter() - start_time) * 1000, 2)

        detections: list[Detection] = []
        for score, text_label, box in zip(scores_t, text_labels, boxes_t):
            x1, y1, x2, y2 = (float(value) for value in box.tolist())
            detections.append(
                Detection(
                    label=_display_label(str(text_label)),
                    confidence=round(float(score), 4),
                    box={
                        "x": round(max(x1, 0.0) / width, 4),
                        "y": round(max(y1, 0.0) / height, 4),
                        "width": round((x2 - x1) / width, 4),
                        "height": round((y2 - y1) / height, 4),
                    },
                )
            )

        detections.sort(key=lambda item: item.confidence, reverse=True)
        detections = detections[: self._settings.detection_max_results]

        return DetectionOutcome(
            detections=detections,
            model_name=self._settings.detection_model_id,
            source="owlvit",
            inference_ms=inference_ms,
            width=width,
            height=height,
        )


@lru_cache(maxsize=1)
def get_detector() -> AerisDetector:
    return AerisDetector()
