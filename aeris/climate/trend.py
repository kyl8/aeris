from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class TrendResult:
    metric: str
    slope_per_year: float | None
    slope_per_decade: float | None
    intercept: float | None
    r2: float | None
    p_value: float | None
    ci95_low_per_decade: float | None
    ci95_high_per_decade: float | None
    n: int
    start_year: int | None
    end_year: int | None
    significant: bool
    confidence: str
    interpretation: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _normal_two_tailed_p_value(t_statistic: float) -> float:
    return math.erfc(abs(t_statistic) / math.sqrt(2.0))


def _student_t_p_value(t_statistic: float, degrees_of_freedom: int) -> float:
    try:
        from scipy import stats  # type: ignore

        return float(2.0 * stats.t.sf(abs(t_statistic), degrees_of_freedom))
    except Exception:
        return _normal_two_tailed_p_value(t_statistic)


def _critical_t_95(degrees_of_freedom: int) -> float:
    try:
        from scipy import stats  # type: ignore

        return float(stats.t.ppf(0.975, degrees_of_freedom))
    except Exception:
        if degrees_of_freedom <= 5:
            return 2.776
        if degrees_of_freedom <= 30:
            return 2.042
        return 1.96


def classify_confidence(*, n: int, p_value: float | None, r2: float | None, coverage_mean: float | None = None) -> str:
    if n < 10 or p_value is None or r2 is None:
        return "low"
    if coverage_mean is not None and coverage_mean < 0.7:
        return "low"
    if p_value <= 0.01 and n >= 40 and r2 >= 0.25:
        return "high"
    if p_value <= 0.05 and n >= 20:
        return "medium"
    return "low"


def _insufficient(metric: str, n: int) -> TrendResult:
    return TrendResult(
        metric=metric,
        slope_per_year=None,
        slope_per_decade=None,
        intercept=None,
        r2=None,
        p_value=None,
        ci95_low_per_decade=None,
        ci95_high_per_decade=None,
        n=n,
        start_year=None,
        end_year=None,
        significant=False,
        confidence="low",
        interpretation="insufficient_data",
    )


def linear_trend(
    df: pd.DataFrame,
    *,
    year_column: str = "year",
    value_column: str = "temperature_mean",
    coverage_column: str | None = "coverage_ratio",
    min_coverage: float = 0.7,
) -> TrendResult:
    if df.empty or year_column not in df.columns or value_column not in df.columns:
        return _insufficient(value_column, 0)

    work = df[[year_column, value_column] + ([coverage_column] if coverage_column and coverage_column in df.columns else [])].copy()
    work[value_column] = pd.to_numeric(work[value_column], errors="coerce")
    work[year_column] = pd.to_numeric(work[year_column], errors="coerce")
    work = work.dropna(subset=[year_column, value_column])
    if coverage_column and coverage_column in work.columns:
        work[coverage_column] = pd.to_numeric(work[coverage_column], errors="coerce")
        work = work.loc[work[coverage_column].fillna(0) >= min_coverage]
    work = work.sort_values(year_column)
    n = int(len(work))
    if n < 3:
        return _insufficient(value_column, n)

    x_years = work[year_column].to_numpy(dtype=float)
    x = x_years - x_years.min()
    y = work[value_column].to_numpy(dtype=float)
    x_mean = float(np.mean(x))
    y_mean = float(np.mean(y))
    sxx = float(np.sum((x - x_mean) ** 2))
    if sxx == 0:
        return _insufficient(value_column, n)

    slope = float(np.sum((x - x_mean) * (y - y_mean)) / sxx)
    intercept = float(y_mean - slope * x_mean)
    predicted = intercept + slope * x
    residuals = y - predicted
    sse = float(np.sum(residuals**2))
    sst = float(np.sum((y - y_mean) ** 2))
    r2 = 0.0 if sst == 0 else max(0.0, 1.0 - sse / sst)
    degrees = n - 2
    mse = sse / degrees if degrees > 0 else 0.0
    slope_se = math.sqrt(mse / sxx) if mse >= 0 else 0.0
    if slope_se == 0:
        t_statistic = math.inf if slope != 0 else 0.0
        p_value = 0.0 if slope != 0 else 1.0
    else:
        t_statistic = slope / slope_se
        p_value = _student_t_p_value(t_statistic, degrees)
    critical = _critical_t_95(degrees)
    ci_low = (slope - critical * slope_se) * 10.0
    ci_high = (slope + critical * slope_se) * 10.0
    coverage_mean = None
    if coverage_column and coverage_column in work.columns:
        coverage_mean = float(work[coverage_column].mean())
    confidence = classify_confidence(n=n, p_value=p_value, r2=r2, coverage_mean=coverage_mean)
    significant = bool(p_value <= 0.05)
    if significant and slope > 0:
        interpretation = "statistically_significant_warming"
    elif significant and slope < 0:
        interpretation = "statistically_significant_cooling"
    elif slope > 0:
        interpretation = "positive_but_not_statistically_significant"
    elif slope < 0:
        interpretation = "negative_but_not_statistically_significant"
    else:
        interpretation = "no_detectable_linear_trend"

    return TrendResult(
        metric=value_column,
        slope_per_year=round(slope, 8),
        slope_per_decade=round(slope * 10.0, 6),
        intercept=round(intercept, 6),
        r2=round(r2, 6),
        p_value=round(float(p_value), 8),
        ci95_low_per_decade=round(ci_low, 6),
        ci95_high_per_decade=round(ci_high, 6),
        n=n,
        start_year=int(x_years.min()),
        end_year=int(x_years.max()),
        significant=significant,
        confidence=confidence,
        interpretation=interpretation,
    )


def trends_by_city(
    annual_summary: pd.DataFrame,
    *,
    value_column: str = "temperature_mean",
    city_column: str = "city",
) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    if annual_summary.empty or city_column not in annual_summary.columns:
        return pd.DataFrame()
    for city, subset in annual_summary.groupby(city_column):
        result = linear_trend(subset, value_column=value_column).to_dict()
        result["city"] = city
        records.append(result)
    return pd.DataFrame(records)


def detect_period_dependency(
    annual_regional: pd.DataFrame,
    periods: Iterable[tuple[str, int, int]],
    *,
    value_column: str = "temperature_mean",
) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for label, start_year, end_year in periods:
        subset = annual_regional.loc[annual_regional["year"].between(start_year, end_year)]
        result = linear_trend(subset, value_column=value_column).to_dict()
        result["period"] = label
        result["requested_start_year"] = start_year
        result["requested_end_year"] = end_year
        records.append(result)
    return pd.DataFrame(records)
