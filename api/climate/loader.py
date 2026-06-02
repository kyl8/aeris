from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd


LOGGER = logging.getLogger("aeris.climate.loader")

TIMESTAMP_COLUMN = "timestamp_meteorologico"
TEMPERATURE_COLUMN = "temperature_2m"

REQUIRED_COLUMNS = [
    "timestamp_meteorologico",
    "latitude",
    "longitude",
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "precipitation",
    "cloud_cover",
    "shortwave_radiation",
    "direct_radiation",
    "diffuse_radiation",
]

NUMERIC_COLUMNS = [
    "latitude",
    "longitude",
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "precipitation",
    "surface_pressure",
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


def validate_required_columns(df: pd.DataFrame) -> None:
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Dataset invalido. Colunas obrigatorias ausentes: {', '.join(missing_columns)}")


def _read_csv(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise ValueError(f"CSV climatico nao encontrado: {csv_path}")

    try:
        return pd.read_csv(csv_path)
    except pd.errors.EmptyDataError as exc:
        raise ValueError(f"CSV climatico vazio ou sem cabecalho: {csv_path}") from exc


def _coerce_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    coerced = df.copy()
    for column in NUMERIC_COLUMNS:
        if column in coerced.columns:
            coerced[column] = pd.to_numeric(coerced[column], errors="coerce")
    return coerced


def _sanitize_ranges(df: pd.DataFrame) -> pd.DataFrame:
    sanitized = df.copy()

    sanitized.loc[~sanitized["latitude"].between(-90, 90), "latitude"] = pd.NA
    sanitized.loc[~sanitized["longitude"].between(-180, 180), "longitude"] = pd.NA

    if "cloud_cover" in sanitized.columns:
        sanitized.loc[~sanitized["cloud_cover"].between(0, 100), "cloud_cover"] = pd.NA

    if "relative_humidity_2m" in sanitized.columns:
        sanitized.loc[~sanitized["relative_humidity_2m"].between(0, 100), "relative_humidity_2m"] = pd.NA

    if "precipitation" in sanitized.columns:
        sanitized.loc[sanitized["precipitation"] < 0, "precipitation"] = pd.NA

    for column in ["cloud_cover_low", "cloud_cover_mid", "cloud_cover_high"]:
        if column in sanitized.columns:
            sanitized.loc[~sanitized[column].between(0, 100), column] = pd.NA

    return sanitized


def load_climate_dataset(csv_path: str | Path) -> pd.DataFrame:
    """Load and validate an Aeris multimodal climate CSV."""

    path = Path(csv_path)
    df = _read_csv(path)
    validate_required_columns(df)

    if df.empty:
        LOGGER.warning("[CLIMATE] Loaded empty dataset: %s", path)
        df[TIMESTAMP_COLUMN] = pd.to_datetime(df[TIMESTAMP_COLUMN])
        return df

    loaded_count = len(df)
    df = df.copy()
    df[TIMESTAMP_COLUMN] = pd.to_datetime(df[TIMESTAMP_COLUMN], errors="coerce")
    df = _coerce_numeric_columns(df)
    df = _sanitize_ranges(df)

    critical_columns = [TIMESTAMP_COLUMN, "latitude", "longitude", TEMPERATURE_COLUMN]
    invalid_mask = df[critical_columns].isna().any(axis=1)
    invalid_count = int(invalid_mask.sum())
    if invalid_count:
        LOGGER.warning("[CLIMATE] Dropping %d invalid climate rows.", invalid_count)
        df = df.loc[~invalid_mask].copy()

    if df.empty and loaded_count > 0:
        raise ValueError("Dataset climatico nao possui linhas validas para analise de temperatura.")

    df = df.sort_values(TIMESTAMP_COLUMN).reset_index(drop=True)
    LOGGER.info("[CLIMATE] Loaded dataset with %d valid records", len(df))
    if not df.empty:
        LOGGER.info(
            "[CLIMATE] Period: %s to %s",
            df[TIMESTAMP_COLUMN].min().date().isoformat(),
            df[TIMESTAMP_COLUMN].max().date().isoformat(),
        )
    return df
