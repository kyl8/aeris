from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def _load_matplotlib() -> Any:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def _save(fig: Any, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    return path


def plot_annual_temperature_trend(annual_regional: pd.DataFrame, trend: dict[str, object], path: Path) -> Path | None:
    if annual_regional.empty:
        return None
    plt = _load_matplotlib()
    fig, ax = plt.subplots(figsize=(10, 5))
    data = annual_regional.sort_values("year")
    ax.plot(data["year"], data["temperature_mean"], color="#235789", linewidth=1.7, label="Temperatura media anual")
    ax.plot(data["year"], data["temperature_mean"].rolling(10, min_periods=3).mean(), color="#d95f02", linewidth=2.1, label="Media movel 10 anos")
    slope = trend.get("slope_per_year")
    intercept = trend.get("intercept")
    if slope is not None and intercept is not None:
        x = data["year"] - data["year"].min()
        ax.plot(data["year"], float(intercept) + float(slope) * x, color="#111111", linestyle="--", label="Tendencia linear")
    ax.set_title("Baixada Santista - tendencia de temperatura anual")
    ax.set_xlabel("Ano")
    ax.set_ylabel("Temperatura media (C)")
    ax.grid(alpha=0.25)
    ax.legend()
    saved = _save(fig, path)
    plt.close(fig)
    return saved


def plot_monthly_temperature_anomalies(monthly_anomalies: pd.DataFrame, path: Path) -> Path | None:
    if monthly_anomalies.empty:
        return None
    plt = _load_matplotlib()
    data = monthly_anomalies.loc[monthly_anomalies["city"] == "regional"].copy()
    if data.empty:
        data = monthly_anomalies.copy()
    pivot = data.pivot_table(index="month", columns="year", values="temperature_anomaly", aggfunc="mean")
    fig, ax = plt.subplots(figsize=(13, 4.8))
    image = ax.imshow(pivot, aspect="auto", cmap="coolwarm", vmin=-3, vmax=3)
    ax.set_title("Anomalias mensais de temperatura vs baseline")
    ax.set_xlabel("Ano")
    ax.set_ylabel("Mes")
    year_labels = list(pivot.columns)
    if year_labels:
        tick_step = max(1, len(year_labels) // 12)
        ax.set_xticks(range(0, len(year_labels), tick_step), [str(year) for year in year_labels[::tick_step]], rotation=45)
    ax.set_yticks(range(len(pivot.index)), [str(month) for month in pivot.index])
    fig.colorbar(image, ax=ax, label="Anomalia (C)")
    saved = _save(fig, path)
    plt.close(fig)
    return saved


def plot_metric_trend(annual_regional: pd.DataFrame, metric: str, ylabel: str, title: str, path: Path) -> Path | None:
    if annual_regional.empty or metric not in annual_regional.columns:
        return None
    plt = _load_matplotlib()
    data = annual_regional.sort_values("year")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(data["year"], data[metric], color="#277da1", linewidth=1.7)
    ax.plot(data["year"], data[metric].rolling(10, min_periods=3).mean(), color="#f8961e", linewidth=2)
    ax.set_title(title)
    ax.set_xlabel("Ano")
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.25)
    saved = _save(fig, path)
    plt.close(fig)
    return saved


def plot_warming_by_city(city_trends: pd.DataFrame, path: Path) -> Path | None:
    if city_trends.empty or "slope_per_decade" not in city_trends.columns:
        return None
    plt = _load_matplotlib()
    data = city_trends.dropna(subset=["slope_per_decade"]).sort_values("slope_per_decade")
    if data.empty:
        return None
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = ["#2a9d8f" if value >= 0 else "#457b9d" for value in data["slope_per_decade"]]
    ax.barh(data["city"], data["slope_per_decade"], color=colors)
    ax.axvline(0, color="#111111", linewidth=0.8)
    ax.set_title("Tendencia de temperatura por cidade")
    ax.set_xlabel("C por decada")
    saved = _save(fig, path)
    plt.close(fig)
    return saved


def plot_data_coverage(monthly_summary: pd.DataFrame, path: Path) -> Path | None:
    if monthly_summary.empty:
        return None
    plt = _load_matplotlib()
    data = monthly_summary.copy()
    pivot = data.pivot_table(index="city", columns="year", values="coverage_ratio", aggfunc="mean")
    fig, ax = plt.subplots(figsize=(12, max(4, len(pivot.index) * 0.45)))
    image = ax.imshow(pivot, aspect="auto", cmap="viridis", vmin=0, vmax=1)
    ax.set_title("Cobertura dos dados por cidade/ano")
    ax.set_xlabel("Ano")
    ax.set_ylabel("Cidade")
    year_labels = list(pivot.columns)
    if year_labels:
        tick_step = max(1, len(year_labels) // 12)
        ax.set_xticks(range(0, len(year_labels), tick_step), [str(year) for year in year_labels[::tick_step]], rotation=45)
    ax.set_yticks(range(len(pivot.index)), list(pivot.index))
    fig.colorbar(image, ax=ax, label="Cobertura")
    saved = _save(fig, path)
    plt.close(fig)
    return saved


def generate_all_plots(
    *,
    output_dir: Path,
    annual_regional: pd.DataFrame,
    monthly_summary: pd.DataFrame,
    monthly_anomalies: pd.DataFrame,
    city_trends: pd.DataFrame,
    trend: dict[str, object],
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    plot_paths: dict[str, str] = {}
    plot_specs = {
        "annual_temperature_trend": plot_annual_temperature_trend(
            annual_regional,
            trend,
            output_dir / "annual_temperature_trend.png",
        ),
        "monthly_temperature_anomalies": plot_monthly_temperature_anomalies(
            monthly_anomalies,
            output_dir / "monthly_temperature_anomalies.png",
        ),
        "precipitation_trend": plot_metric_trend(
            annual_regional,
            "precipitation_sum",
            "Precipitacao acumulada media (mm)",
            "Baixada Santista - precipitacao anual",
            output_dir / "precipitation_trend.png",
        ),
        "humidity_trend": plot_metric_trend(
            annual_regional,
            "humidity_mean",
            "Umidade relativa media (%)",
            "Baixada Santista - umidade anual",
            output_dir / "humidity_trend.png",
        ),
        "warming_by_city": plot_warming_by_city(city_trends, output_dir / "warming_by_city.png"),
        "data_coverage": plot_data_coverage(monthly_summary, output_dir / "data_coverage.png"),
    }
    for name, path in plot_specs.items():
        if path is not None:
            plot_paths[name] = str(path)
    return plot_paths
