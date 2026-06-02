from __future__ import annotations

from collections import Counter
from typing import Any

import pandas as pd


def label_counts(df: pd.DataFrame, label_column: str = "visual_label") -> dict[str, int]:
    if df.empty or label_column not in df.columns:
        return {}
    return {str(label): int(count) for label, count in df[label_column].value_counts().items()}


def compute_class_weights(df: pd.DataFrame, label_column: str = "visual_label") -> dict[str, float]:
    counts = label_counts(df, label_column)
    if not counts:
        return {}
    total = sum(counts.values())
    class_count = len(counts)
    return {label: round(total / (class_count * count), 6) for label, count in counts.items() if count > 0}


def oversample_minority(df: pd.DataFrame, label_column: str = "visual_label", target_count: int | None = None) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    counts = df[label_column].value_counts()
    target = target_count or int(counts.max())
    parts = []
    for _, subset in df.groupby(label_column):
        if len(subset) >= target:
            parts.append(subset)
        else:
            parts.append(subset.sample(n=target, replace=True, random_state=42))
    return pd.concat(parts, ignore_index=True).sample(frac=1.0, random_state=42).reset_index(drop=True)


def undersample_majority(df: pd.DataFrame, label_column: str = "visual_label", target_count: int | None = None) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    counts = df[label_column].value_counts()
    target = target_count or int(counts.min())
    parts = [subset.sample(n=min(len(subset), target), random_state=42) for _, subset in df.groupby(label_column)]
    return pd.concat(parts, ignore_index=True).sample(frac=1.0, random_state=42).reset_index(drop=True)


def hard_negative_candidates(
    df: pd.DataFrame,
    *,
    label_column: str = "visual_label",
    confidence_column: str = "visual_confidence",
    min_confidence: float = 0.35,
    max_confidence: float = 0.65,
) -> pd.DataFrame:
    if df.empty or confidence_column not in df.columns:
        return pd.DataFrame()
    confidence = pd.to_numeric(df[confidence_column], errors="coerce")
    candidates = df.loc[confidence.between(min_confidence, max_confidence)].copy()
    if "weather_label" in candidates.columns:
        candidates = candidates.loc[candidates[label_column] != candidates["weather_label"]]
    return candidates


def confidence_filter(
    df: pd.DataFrame,
    *,
    min_visual_confidence: float = 0.5,
    min_weather_confidence: float = 0.5,
) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    visual = pd.to_numeric(df.get("visual_confidence", 1.0), errors="coerce").fillna(0)
    weather = pd.to_numeric(df.get("weather_confidence", 1.0), errors="coerce").fillna(0)
    return df.loc[(visual >= min_visual_confidence) & (weather >= min_weather_confidence)].copy()


def balance_dataset(
    df: pd.DataFrame,
    *,
    strategy: str = "class_weights",
    label_column: str = "visual_label",
    target_count: int | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    filtered = confidence_filter(df)
    before = label_counts(filtered, label_column)
    if strategy == "oversample":
        balanced = oversample_minority(filtered, label_column, target_count=target_count)
    elif strategy == "undersample":
        balanced = undersample_majority(filtered, label_column, target_count=target_count)
    elif strategy == "none":
        balanced = filtered
    else:
        balanced = filtered
    after = label_counts(balanced, label_column)
    hard_negatives = hard_negative_candidates(filtered, label_column=label_column)
    metadata = {
        "strategy": strategy,
        "before_counts": before,
        "after_counts": after,
        "class_weights": compute_class_weights(filtered, label_column),
        "hard_negative_count": int(len(hard_negatives)),
        "imbalanced_classes": _imbalanced_classes(after),
    }
    return balanced.reset_index(drop=True), metadata


def _imbalanced_classes(counts: dict[str, int], ratio_threshold: float = 0.35) -> list[str]:
    if not counts:
        return []
    max_count = max(counts.values())
    return [label for label, count in counts.items() if max_count and count / max_count < ratio_threshold]
