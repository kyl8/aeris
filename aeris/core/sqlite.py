from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(slots=True)
class MetadataStore:
    """SQLite metadata store for resumable, auditable pipeline runs."""

    path: Path

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                create table if not exists downloads (
                    id text primary key,
                    source text not null,
                    url text,
                    local_path text,
                    status text not null,
                    checksum text,
                    metadata_json text,
                    created_at text not null,
                    updated_at text not null
                );

                create table if not exists samples (
                    id text primary key,
                    image_path text,
                    thumbnail_path text,
                    source_image text,
                    source_weather text,
                    timestamp_image text,
                    timestamp_weather text,
                    latitude real,
                    longitude real,
                    country text,
                    biome text,
                    visual_label text,
                    visual_confidence real,
                    weather_label text,
                    weather_confidence real,
                    weather_json text,
                    quality_json text,
                    metadata_json text,
                    created_at text not null,
                    updated_at text not null
                );

                create table if not exists retry_queue (
                    id integer primary key autoincrement,
                    task_type text not null,
                    payload_json text not null,
                    attempts integer not null default 0,
                    last_error text,
                    status text not null default 'pending',
                    created_at text not null,
                    updated_at text not null
                );

                create table if not exists run_events (
                    id integer primary key autoincrement,
                    run_id text,
                    module text,
                    level text,
                    event text,
                    payload_json text,
                    created_at text not null
                );
                """
            )

    def upsert_download(
        self,
        *,
        download_id: str,
        source: str,
        status: str,
        url: str | None = None,
        local_path: str | None = None,
        checksum: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        now = _utc_now()
        with self.connect() as connection:
            connection.execute(
                """
                insert into downloads (
                    id, source, url, local_path, status, checksum, metadata_json, created_at, updated_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(id) do update set
                    source=excluded.source,
                    url=excluded.url,
                    local_path=excluded.local_path,
                    status=excluded.status,
                    checksum=excluded.checksum,
                    metadata_json=excluded.metadata_json,
                    updated_at=excluded.updated_at
                """,
                (
                    download_id,
                    source,
                    url,
                    local_path,
                    status,
                    checksum,
                    json.dumps(metadata or {}, ensure_ascii=False),
                    now,
                    now,
                ),
            )

    def upsert_sample(self, sample: dict[str, Any]) -> None:
        now = _utc_now()
        payload = dict(sample)
        weather = payload.pop("weather", {})
        quality = payload.pop("quality", {})
        metadata = payload.pop("metadata", {})
        with self.connect() as connection:
            connection.execute(
                """
                insert into samples (
                    id, image_path, thumbnail_path, source_image, source_weather,
                    timestamp_image, timestamp_weather, latitude, longitude, country,
                    biome, visual_label, visual_confidence, weather_label,
                    weather_confidence, weather_json, quality_json, metadata_json,
                    created_at, updated_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(id) do update set
                    image_path=excluded.image_path,
                    thumbnail_path=excluded.thumbnail_path,
                    source_image=excluded.source_image,
                    source_weather=excluded.source_weather,
                    timestamp_image=excluded.timestamp_image,
                    timestamp_weather=excluded.timestamp_weather,
                    latitude=excluded.latitude,
                    longitude=excluded.longitude,
                    country=excluded.country,
                    biome=excluded.biome,
                    visual_label=excluded.visual_label,
                    visual_confidence=excluded.visual_confidence,
                    weather_label=excluded.weather_label,
                    weather_confidence=excluded.weather_confidence,
                    weather_json=excluded.weather_json,
                    quality_json=excluded.quality_json,
                    metadata_json=excluded.metadata_json,
                    updated_at=excluded.updated_at
                """,
                (
                    payload.get("id"),
                    payload.get("image_path"),
                    payload.get("thumbnail_path"),
                    payload.get("source_image"),
                    payload.get("source_weather"),
                    payload.get("timestamp_image"),
                    payload.get("timestamp_weather"),
                    payload.get("latitude"),
                    payload.get("longitude"),
                    payload.get("country"),
                    payload.get("biome"),
                    payload.get("visual_label"),
                    payload.get("visual_confidence"),
                    payload.get("weather_label"),
                    payload.get("weather_confidence"),
                    json.dumps(weather, ensure_ascii=False),
                    json.dumps(quality, ensure_ascii=False),
                    json.dumps(metadata, ensure_ascii=False),
                    now,
                    now,
                ),
            )

    def add_retry_task(self, task_type: str, payload: dict[str, Any], error: str | None = None) -> None:
        now = _utc_now()
        with self.connect() as connection:
            connection.execute(
                """
                insert into retry_queue (task_type, payload_json, last_error, created_at, updated_at)
                values (?, ?, ?, ?, ?)
                """,
                (task_type, json.dumps(payload, ensure_ascii=False), error, now, now),
            )

    def pending_retry_tasks(self, task_type: str | None = None) -> list[dict[str, Any]]:
        query = "select * from retry_queue where status='pending'"
        params: list[Any] = []
        if task_type is not None:
            query += " and task_type=?"
            params.append(task_type)
        with self.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def record_event(self, *, run_id: str | None, module: str, level: str, event: str, payload: dict[str, Any]) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                insert into run_events (run_id, module, level, event, payload_json, created_at)
                values (?, ?, ?, ?, ?, ?)
                """,
                (run_id, module, level, event, json.dumps(payload, ensure_ascii=False), _utc_now()),
            )

    def iter_samples(self) -> Iterable[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute("select * from samples order by timestamp_image").fetchall()
        for row in rows:
            payload = dict(row)
            payload["weather"] = json.loads(payload.pop("weather_json") or "{}")
            payload["quality"] = json.loads(payload.pop("quality_json") or "{}")
            payload["metadata"] = json.loads(payload.pop("metadata_json") or "{}")
            yield payload
