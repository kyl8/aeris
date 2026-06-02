from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

import pandas as pd


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None or pd.isna(value):
        return "indisponivel"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _records_table(records: list[dict[str, Any]], columns: list[str]) -> str:
    if not records:
        return "_Sem registros._"
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    rows = []
    for record in records:
        rows.append("| " + " | ".join(_fmt(record.get(column)) for column in columns) + " |")
    return "\n".join([header, sep, *rows])


def build_executive_conclusion(trend: dict[str, Any], period: dict[str, Any], region_name: str) -> str:
    slope = trend.get("slope_per_decade")
    p_value = trend.get("p_value")
    ci_low = trend.get("ci95_low_per_decade")
    ci_high = trend.get("ci95_high_per_decade")
    significant = bool(trend.get("significant"))
    confidence = trend.get("confidence", "low")
    start = period.get("start_year")
    end = period.get("end_year")

    if slope is None:
        return (
            f"Com base nos dados disponiveis para {region_name}, nao ha pontos suficientes "
            "para estimar uma tendencia linear robusta."
        )

    direction = "aquecimento regional" if slope > 0 else "resfriamento regional"
    evidence = "estatisticamente significativa" if significant else "nao estatisticamente significativa"
    return (
        f"Com base nos dados ERA5/Open-Meteo de {start} a {end} para {region_name}, "
        f"a tendencia estimada foi de {_fmt(float(slope), 3)} C/decada "
        f"(IC95% {_fmt(ci_low, 3)} a {_fmt(ci_high, 3)}; p-value {_fmt(p_value, 5)}). "
        f"Isso indica uma tendencia {evidence} compatível com {direction}, com confianca {confidence}. "
        "Essa analise nao atribui causalidade exclusiva ao aquecimento global: urbanizacao, ilha de calor, "
        "variabilidade natural, vieses do ERA5 e resolucao espacial tambem precisam ser considerados."
    )


def generate_markdown_report(result: dict[str, Any]) -> str:
    region = result["region"]
    period = result["period"]
    trend = result["regional_trend"]
    plots = result.get("plots", {})
    top_warm = result.get("top_warm_years", [])
    top_cold = result.get("top_cold_years", [])
    period_comparison = result.get("period_comparison", [])
    city_trends = result.get("city_trends", [])
    coverage = result.get("coverage", {})

    lines = [
        "# Aeris Climate Report - Baixada Santista",
        "",
        "## Resumo executivo",
        "",
        build_executive_conclusion(trend, period, region["name"]),
        "",
        "## Metodologia",
        "",
        (
            "A analise usa dados horarios historicos Open-Meteo Historical Weather API com modelo de reanalysis "
            f"{result['source_weather']}. Os dados meteorologicos sao tratados como features tabulares e reanalysis, "
            "nao como fotografias ou imagens de satelite."
        ),
        "",
        (
            f"Regiao: {region['name']} (`{region['slug']}`), bbox {region['bbox']}. "
            f"Coordenadas analisadas: {len(region['coordinates'])}."
        ),
        "",
        (
            "A tendencia linear foi calculada sobre medias anuais regionais. O intervalo de confianca de 95%, "
            "p-value e R2 sao derivados da regressao linear. Anomalias mensais usam baseline configuravel "
            f"{result['baseline']['start_year']}-{result['baseline']['end_year']}."
        ),
        "",
        "## Resultado regional",
        "",
        f"- Periodo analisado: {period.get('start_year')} a {period.get('end_year')}",
        f"- Slope: {_fmt(trend.get('slope_per_decade'), 4)} C/decada",
        f"- IC95%: {_fmt(trend.get('ci95_low_per_decade'), 4)} a {_fmt(trend.get('ci95_high_per_decade'), 4)} C/decada",
        f"- p-value: {_fmt(trend.get('p_value'), 6)}",
        f"- R2: {_fmt(trend.get('r2'), 4)}",
        f"- Significativo a 5%: {trend.get('significant')}",
        f"- Confianca: {trend.get('confidence')}",
        "",
        "## Cobertura dos dados",
        "",
        f"- Registros horarios processados: {coverage.get('hourly_rows')}",
        f"- Meses agregados: {coverage.get('monthly_rows')}",
        f"- Anos agregados: {coverage.get('annual_rows')}",
        f"- Lacunas mensais abaixo do limiar: {coverage.get('monthly_gap_count')}",
        "",
        "## Comparacao de periodos",
        "",
        _records_table(period_comparison, ["period", "temperature_mean", "precipitation_sum_mean", "coverage_ratio_mean"]),
        "",
        "## Tendencia por cidade",
        "",
        _records_table(city_trends, ["city", "slope_per_decade", "p_value", "r2", "confidence", "interpretation"]),
        "",
        "## Top 10 anos mais quentes",
        "",
        _records_table(top_warm, ["city", "year", "temperature_anomaly", "positive_months", "months"]),
        "",
        "## Top 10 anos mais frios",
        "",
        _records_table(top_cold, ["city", "year", "temperature_anomaly", "negative_months", "months"]),
        "",
        "## Graficos",
        "",
    ]

    for name, plot_path in plots.items():
        relative = Path(plot_path).name if Path(plot_path).parent.name == "plots" else plot_path
        lines.extend([f"### {name}", "", f"![{name}](plots/{relative})", ""])

    lines.extend(
        [
            "## Limitacoes",
            "",
            "- ERA5/Open-Meteo e reanalysis: combina observacoes e modelo fisico para preencher lacunas.",
            "- A resolucao espacial pode suavizar microclimas costeiros e efeitos de ilha de calor urbana.",
            "- Atribuicao causal ao aquecimento global exige comparacao com multiplas fontes e desenho estatistico especifico.",
            "- Mudancas de uso do solo, urbanizacao, topografia e brisa maritima podem influenciar a serie regional.",
            "- Variabilidade natural interanual pode alterar conclusoes quando o periodo escolhido muda.",
            "",
            "## Conclusao",
            "",
            build_executive_conclusion(trend, period, region["name"]),
            "",
            "## Metadados",
            "",
            "```json",
            json.dumps(result.get("metadata", {}), ensure_ascii=False, indent=2),
            "```",
        ],
    )
    return "\n".join(lines)


def markdown_to_html(markdown: str, title: str = "Aeris Climate Report") -> str:
    try:
        import markdown as markdown_lib  # type: ignore

        body = markdown_lib.markdown(markdown, extensions=["tables", "fenced_code"])
    except Exception:
        escaped = html.escape(markdown)
        body = "<pre>" + escaped + "</pre>"
    return (
        "<!doctype html><html lang=\"pt-BR\"><head><meta charset=\"utf-8\">"
        f"<title>{html.escape(title)}</title>"
        "<style>"
        "body{font-family:Inter,Segoe UI,Arial,sans-serif;max-width:1100px;margin:40px auto;padding:0 24px;line-height:1.55;color:#17202a}"
        "table{border-collapse:collapse;width:100%;margin:16px 0}td,th{border:1px solid #d6dee6;padding:6px 8px;text-align:left}"
        "th{background:#eef3f7}img{max-width:100%;height:auto}code,pre{background:#f5f7f9}"
        "</style></head><body>"
        f"{body}</body></html>"
    )


def write_reports(result: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    markdown = generate_markdown_report(result)
    markdown_path = output_dir / "report.md"
    html_path = output_dir / "report.html"
    markdown_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(markdown_to_html(markdown), encoding="utf-8")
    return markdown_path, html_path
