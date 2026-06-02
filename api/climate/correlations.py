from __future__ import annotations

import math

import pandas as pd


CORRELATION_VARIABLES = [
    "relative_humidity_2m",
    "dew_point_2m",
    "precipitation",
    "cloud_cover",
    "cloud_cover_low",
    "cloud_cover_mid",
    "cloud_cover_high",
    "shortwave_radiation",
    "direct_radiation",
    "diffuse_radiation",
    "wind_speed_10m",
    "wind_gusts_10m",
]

INTERPRETATION_LABELS = {
    "relative_humidity_2m": "umidade relativa",
    "dew_point_2m": "ponto de orvalho",
    "precipitation": "precipitacao",
    "cloud_cover": "cobertura de nuvens",
    "cloud_cover_low": "nuvens baixas",
    "cloud_cover_mid": "nuvens medias",
    "cloud_cover_high": "nuvens altas",
    "shortwave_radiation": "radiacao solar de onda curta",
    "direct_radiation": "radiacao direta",
    "diffuse_radiation": "radiacao difusa",
    "wind_speed_10m": "velocidade do vento",
    "wind_gusts_10m": "rajadas de vento",
}


def _strength_label(correlation: float) -> str:
    absolute = abs(correlation)
    if absolute >= 0.5:
        return "forte"
    if absolute >= 0.3:
        return "moderada"
    return "fraca"


def interpret_correlations(correlations: dict[str, float]) -> list[str]:
    interpretation: list[str] = []
    for variable, correlation in sorted(correlations.items(), key=lambda item: abs(item[1]), reverse=True):
        if abs(correlation) < 0.3:
            continue
        label = INTERPRETATION_LABELS.get(variable, variable)
        direction = "positiva" if correlation > 0 else "negativa"
        strength = _strength_label(correlation)
        if correlation > 0:
            interpretation.append(
                f"Temperaturas maiores aparecem associadas a maior {label} (associacao {direction} {strength}).",
            )
        else:
            interpretation.append(
                f"Temperaturas maiores aparecem associadas a menor {label} (associacao {direction} {strength}).",
            )

    if not interpretation:
        interpretation.append("Nao foram encontradas correlacoes meteorologicas moderadas ou fortes com temperatura.")
    return interpretation


def compute_climate_correlations(df: pd.DataFrame) -> dict[str, object]:
    if df.empty or "temperature_2m" not in df.columns:
        return {"correlations": {}, "interpretation": ["Dados insuficientes para correlacoes."]}

    correlations: dict[str, float] = {}
    for variable in CORRELATION_VARIABLES:
        if variable not in df.columns:
            continue
        pair = df[["temperature_2m", variable]].dropna()
        if len(pair) < 2:
            continue
        value = pair["temperature_2m"].corr(pair[variable])
        if value is None or math.isnan(float(value)):
            continue
        correlations[variable] = round(float(value), 4)

    return {
        "correlations": correlations,
        "interpretation": interpret_correlations(correlations),
    }
