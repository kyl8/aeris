from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
import sys


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }

        for attribute in ("method", "path", "status_code", "duration_ms", "client_ip", "model_name", "model_path"):
            value = record.__dict__.get(attribute)
            if value is not None:
                payload[attribute] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "api"):
        named_logger = logging.getLogger(logger_name)
        named_logger.handlers.clear()
        named_logger.propagate = True
        named_logger.setLevel(level)

    logging.captureWarnings(True)