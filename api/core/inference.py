from statistics import fmean

from .model import discover_model_artifact
from .preprocessing import coerce_features, normalize_features


def run_inference(features: list[float]) -> dict[str, object]:
    cleaned_features = coerce_features(features)
    normalized_features = normalize_features(cleaned_features)
    model_artifact = discover_model_artifact()

    return {
        "model_name": model_artifact.name,
        "model_version": model_artifact.version,
        "artifact_path": str(model_artifact.path) if model_artifact.path else None,
        "feature_count": len(cleaned_features),
        "prediction": round(fmean(normalized_features), 4),
        "normalized_features": normalized_features,
        "detail": "Resultado base calculado a partir do vetor recebido. Substitua por um modelo treinado em weights/ quando ele estiver pronto.",
    }