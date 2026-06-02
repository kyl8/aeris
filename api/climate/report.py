from __future__ import annotations

from typing import Any

import pandas as pd


def generate_climate_warnings(df: pd.DataFrame, trend_result: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    years_covered = float(trend_result.get("years_covered") or 0)
    sample_count = int(trend_result.get("sample_count") or 0)

    if years_covered < 10:
        warnings.append("Serie historica curta demais para afirmar aquecimento global com alta confianca.")
    if sample_count < 365:
        warnings.append("Poucas amostras para uma analise climatica robusta.")
    if trend_result.get("confidence") == "low":
        warnings.append("Confianca estatistica baixa; interprete como analise exploratoria.")

    warnings.append("Imagem isolada nao deve ser usada como prova direta de aquecimento global.")
    warnings.append("Resultado representa sinal local/regional no dataset analisado, nao uma conclusao global.")
    warnings.append("Para conclusoes climaticas fortes, use series de decadas e fontes oficiais.")
    return warnings


def build_final_assessment(
    trend_result: dict[str, Any],
    anomaly_result: dict[str, Any],
    extremes_result: dict[str, Any],
) -> dict[str, str]:
    trend = str(trend_result.get("trend", "insufficient_data"))
    confidence = str(trend_result.get("confidence", "low"))
    slope = float(trend_result.get("slope_celsius_per_year") or 0)
    hot_frequency = str(extremes_result.get("hot_extreme_frequency", "insufficient_data"))
    positive_anomaly_frequency = str(anomaly_result.get("positive_anomaly_frequency", "insufficient_data"))

    if trend == "insufficient_data":
        label = "insufficient_data"
        summary = "Dados insuficientes para avaliar tendencia local de aquecimento."
    elif trend == "increasing" and slope > 0.03 and confidence in {"medium", "high"}:
        label = "local_warming_signal_detected"
        summary = "A serie mostra tendencia positiva de temperatura com confianca estatistica moderada ou alta."
    elif trend == "increasing":
        label = "possible_local_warming_signal"
        summary = "A serie sugere possivel sinal local de aquecimento, mas a confianca ainda e limitada."
    elif trend == "decreasing":
        label = "cooling_signal_detected"
        summary = "A serie mostra tendencia negativa de temperatura no dataset analisado."
    else:
        label = "no_clear_warming_signal"
        summary = "A serie nao mostra sinal claro de aquecimento no dataset analisado."

    if label in {"local_warming_signal_detected", "possible_local_warming_signal"}:
        if hot_frequency == "increasing":
            summary += " A frequencia de extremos quentes tambem aparece em alta."
        if positive_anomaly_frequency == "above_normal":
            summary += " Anomalias positivas aparecem acima do normal no periodo."

    return {
        "label": label,
        "confidence": confidence,
        "summary": summary,
    }


def _fmt(value: Any, suffix: str = "") -> str:
    if value is None:
        return "indisponivel"
    if isinstance(value, float):
        return f"{value:+0.2f}{suffix}"
    return f"{value}{suffix}"


def generate_climate_report(result: dict[str, Any]) -> str:
    region = result.get("region") or "regiao analisada"
    period = result.get("period", {})
    trend = result.get("trend_analysis", {})
    anomalies = result.get("anomaly_analysis", {})
    assessment = result.get("final_assessment", {})

    start = period.get("start", "inicio indisponivel")
    end = period.get("end", "fim indisponivel")
    slope_year = _fmt(trend.get("slope_celsius_per_year"), " C/ano")
    slope_decade = _fmt(trend.get("slope_celsius_per_decade"), " C/decada")
    latest_anomaly = _fmt(anomalies.get("latest_anomaly_celsius"), " C")

    lines = [
        "Aeris Climate Report",
        "",
        f"Entre {start} e {end}, a regiao {region} foi analisada com dados meteorologicos historicos.",
        (
            f"A tendencia estimada foi '{trend.get('trend', 'indisponivel')}', "
            f"com inclinacao de {slope_year}, equivalente a {slope_decade}."
        ),
        f"A anomalia termica mais recente ficou em {latest_anomaly} em relacao a baseline mensal.",
        "",
        str(assessment.get("summary", "Avaliacao final indisponivel.")),
        (
            "Esse resultado nao deve ser interpretado sozinho como prova definitiva de aquecimento global. "
            "A confianca depende da duracao da serie, quantidade de amostras e distribuicao temporal."
        ),
        "",
        "Imagem e cenas de satelite foram usadas apenas como contexto visual de superficie, nuvens e cobertura da regiao.",
    ]
    return "\n".join(lines)
