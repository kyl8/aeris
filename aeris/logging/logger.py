from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

from .formatters import AerisJsonFormatter, AerisTextFormatter


def configure_logging(level: str = "INFO", *, json_format: bool = False) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(AerisJsonFormatter() if json_format else AerisTextFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level.upper())
    logging.captureWarnings(True)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_event(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    logger.log(level, event, extra={key: value for key, value in fields.items() if value is not None})


@dataclass(slots=True)
class RunLogger:
    """Small helper for consistent progress and audit logs."""

    logger: logging.Logger
    region: str | None = None
    period: str | None = None
    source: str | None = None
    module: str | None = None
    base_fields: dict[str, Any] = field(default_factory=dict)
    started_at: float = field(default_factory=perf_counter)

    def child(self, **fields: Any) -> "RunLogger":
        merged = dict(self.base_fields)
        merged.update({key: value for key, value in fields.items() if value is not None})
        return RunLogger(
            logger=self.logger,
            region=fields.get("region", self.region),
            period=fields.get("period", self.period),
            source=fields.get("source", self.source),
            module=fields.get("module", self.module),
            base_fields=merged,
            started_at=self.started_at,
        )

    def _fields(self, **fields: Any) -> dict[str, Any]:
        payload = dict(self.base_fields)
        payload.update(
            {
                "region": self.region,
                "period": self.period,
                "source": self.source,
                "elapsed_seconds": round(perf_counter() - self.started_at, 3),
            },
        )
        payload.update(fields)
        return {key: value for key, value in payload.items() if value is not None}

    def debug(self, event: str, **fields: Any) -> None:
        log_event(self.logger, logging.DEBUG, event, **self._fields(**fields))

    def info(self, event: str, **fields: Any) -> None:
        log_event(self.logger, logging.INFO, event, **self._fields(**fields))

    def warn(self, event: str, **fields: Any) -> None:
        log_event(self.logger, logging.WARNING, event, **self._fields(**fields))

    def error(self, event: str, **fields: Any) -> None:
        log_event(self.logger, logging.ERROR, event, **self._fields(**fields))

    def critical(self, event: str, **fields: Any) -> None:
        log_event(self.logger, logging.CRITICAL, event, **self._fields(**fields))

    def progress(self, event: str, *, current: int, total: int, **fields: Any) -> None:
        progress = 0.0 if total <= 0 else round((current / total) * 100.0, 2)
        elapsed = perf_counter() - self.started_at
        eta_seconds = None
        if current > 0 and total > current:
            eta_seconds = round((elapsed / current) * (total - current), 2)
        self.info(
            event,
            current=current,
            total=total,
            progress_percent=progress,
            eta_seconds=eta_seconds,
            **fields,
        )

    def summary(self, event: str = "run_completed", **fields: Any) -> None:
        self.info(event, duration_seconds=round(perf_counter() - self.started_at, 3), **fields)
