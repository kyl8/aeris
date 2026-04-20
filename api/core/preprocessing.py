from math import isfinite


def coerce_features(features: list[float]) -> list[float]:
    cleaned_features: list[float] = []

    for raw_value in features:
        value = float(raw_value)
        if isfinite(value):
            cleaned_features.append(value)

    if not cleaned_features:
        raise ValueError("Pelo menos um valor numérico finito é necessário.")

    return cleaned_features


def normalize_features(features: list[float]) -> list[float]:
    scale = max(abs(value) for value in features)
    if scale == 0:
        return [0.0 for _ in features]

    return [round(value / scale, 6) for value in features]