from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any


RESERVED_LOG_RECORD_KEYS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def extract_extra(record: logging.LogRecord) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in record.__dict__.items():
        if key in RESERVED_LOG_RECORD_KEYS or key.startswith("_"):
            continue
        if value is None:
            continue
        payload[key] = value
    return payload


def _json_default(value: Any) -> str:
    return str(value)


def logfmt_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    raw = str(value)
    if not raw:
        return '""'
    if any(char.isspace() for char in raw) or '"' in raw or "=" in raw:
        escaped = raw.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return raw


class AerisTextFormatter(logging.Formatter):
    """Human-readable structured logs matching long-running pipeline needs."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = utc_now_iso()
        parts = [
            f"[{timestamp}]",
            f"[{record.levelname}]",
            f"[{record.name}]",
            str(record.getMessage()),
        ]
        extras = extract_extra(record)
        if extras:
            parts.append(" ".join(f"{key}={logfmt_value(value)}" for key, value in sorted(extras.items())))
        if record.exc_info:
            parts.append(self.formatException(record.exc_info))
        return " ".join(parts)


class AerisJsonFormatter(logging.Formatter):
    """Machine-readable JSON logs for audit trails and ingestion systems."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": utc_now_iso(),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }
        payload.update(extract_extra(record))
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=_json_default)
