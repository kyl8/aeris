from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from functools import lru_cache
from pathlib import Path
from threading import Lock
import logging
import sqlite3

from .config import get_settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PredictionRecord:
    id: int | None
    created_at: datetime
    climate_class: str
    confidence: float
    heatmap: str | None
    model_name: str
    model_version: str
    source: str
    inference_ms: float
    image_name: str | None = None

    def to_payload(self) -> dict[str, object]:
        payload = asdict(self)
        payload["class"] = payload.pop("climate_class")
        return payload


class PredictionStore:
    def save(self, record: PredictionRecord) -> PredictionRecord:
        raise NotImplementedError

    def list(
        self,
        *,
        date_filter: date | None = None,
        prediction_class: str | None = None,
    ) -> list[PredictionRecord]:
        raise NotImplementedError


class InMemoryPredictionStore(PredictionStore):
    def __init__(self) -> None:
        self._lock = Lock()
        self._records: list[PredictionRecord] = []
        self._counter = 0

    def save(self, record: PredictionRecord) -> PredictionRecord:
        with self._lock:
            self._counter += 1
            stored = PredictionRecord(
                id=self._counter,
                created_at=record.created_at.astimezone(timezone.utc),
                climate_class=record.climate_class,
                confidence=record.confidence,
                heatmap=record.heatmap,
                model_name=record.model_name,
                model_version=record.model_version,
                source=record.source,
                inference_ms=record.inference_ms,
                image_name=record.image_name,
            )
            self._records.append(stored)
            return stored

    def list(
        self,
        *,
        date_filter: date | None = None,
        prediction_class: str | None = None,
    ) -> list[PredictionRecord]:
        with self._lock:
            records = list(self._records)

        return _filter_records(records, date_filter=date_filter, prediction_class=prediction_class)


class SQLitePredictionStore(PredictionStore):
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    climate_class TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    heatmap TEXT,
                    model_name TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    source TEXT NOT NULL,
                    inference_ms REAL NOT NULL,
                    image_name TEXT
                )
                """
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_predictions_created_at ON predictions(created_at)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_predictions_class ON predictions(climate_class)")

    def save(self, record: PredictionRecord) -> PredictionRecord:
        created_at = record.created_at.astimezone(timezone.utc)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO predictions (
                    created_at,
                    climate_class,
                    confidence,
                    heatmap,
                    model_name,
                    model_version,
                    source,
                    inference_ms,
                    image_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    created_at.isoformat(),
                    record.climate_class,
                    record.confidence,
                    record.heatmap,
                    record.model_name,
                    record.model_version,
                    record.source,
                    record.inference_ms,
                    record.image_name,
                ),
            )
            connection.commit()

        return PredictionRecord(
            id=cursor.lastrowid,
            created_at=created_at,
            climate_class=record.climate_class,
            confidence=record.confidence,
            heatmap=record.heatmap,
            model_name=record.model_name,
            model_version=record.model_version,
            source=record.source,
            inference_ms=record.inference_ms,
            image_name=record.image_name,
        )

    def list(
        self,
        *,
        date_filter: date | None = None,
        prediction_class: str | None = None,
    ) -> list[PredictionRecord]:
        query = [
            "SELECT id, created_at, climate_class, confidence, heatmap, model_name, model_version, source, inference_ms, image_name",
            "FROM predictions",
        ]
        conditions: list[str] = []
        parameters: list[object] = []

        if date_filter is not None:
            conditions.append("date(created_at) = ?")
            parameters.append(date_filter.isoformat())

        if prediction_class is not None:
            conditions.append("climate_class = ?")
            parameters.append(prediction_class)

        if conditions:
            query.append("WHERE " + " AND ".join(conditions))

        query.append("ORDER BY created_at DESC, id DESC")

        with self._connect() as connection:
            rows = connection.execute("\n".join(query), parameters).fetchall()

        return [
            PredictionRecord(
                id=row["id"],
                created_at=datetime.fromisoformat(row["created_at"]),
                climate_class=row["climate_class"],
                confidence=row["confidence"],
                heatmap=row["heatmap"],
                model_name=row["model_name"],
                model_version=row["model_version"],
                source=row["source"],
                inference_ms=row["inference_ms"],
                image_name=row["image_name"],
            )
            for row in rows
        ]


def _filter_records(
    records: list[PredictionRecord],
    *,
    date_filter: date | None,
    prediction_class: str | None,
) -> list[PredictionRecord]:
    filtered_records = records

    if date_filter is not None:
        filtered_records = [record for record in filtered_records if record.created_at.date() == date_filter]

    if prediction_class is not None:
        filtered_records = [record for record in filtered_records if record.climate_class == prediction_class]

    return sorted(filtered_records, key=lambda record: (record.created_at, record.id or 0), reverse=True)


def _build_prediction_store() -> PredictionStore:
    settings = get_settings()

    try:
        return SQLitePredictionStore(settings.history_db_path)
    except Exception:  
        logger.exception("Falha ao iniciar o armazenamento SQLite. Usando armazenamento em memória como fallback.")
        return InMemoryPredictionStore()


@lru_cache(maxsize=1)
def get_history_store() -> PredictionStore:
    return _build_prediction_store()