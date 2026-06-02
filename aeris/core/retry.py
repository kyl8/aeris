from __future__ import annotations

import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Callable, TypeVar


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class RetryConfig:
    attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    jitter_seconds: float = 0.25

    def delay_for_attempt(self, attempt_index: int) -> float:
        delay = min(self.max_delay_seconds, self.base_delay_seconds * (2 ** max(0, attempt_index - 1)))
        if self.jitter_seconds > 0:
            delay += random.uniform(0, self.jitter_seconds)
        return delay


def _retry_after_delay(exc: BaseException) -> float | None:
    explicit = getattr(exc, "retry_after_seconds", None)
    if isinstance(explicit, (int, float)) and explicit > 0:
        return float(explicit)

    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    retry_after = headers.get("Retry-After")
    if not retry_after:
        return None
    try:
        return max(0.0, float(retry_after))
    except ValueError:
        pass
    try:
        retry_at = parsedate_to_datetime(retry_after)
    except (TypeError, ValueError):
        return None
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=timezone.utc)
    return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())


def retry_sync(
    operation: Callable[[], T],
    *,
    config: RetryConfig | None = None,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
    on_retry: Callable[[int, BaseException, float], None] | None = None,
) -> T:
    retry_config = config or RetryConfig()
    last_error: BaseException | None = None
    for attempt in range(1, retry_config.attempts + 1):
        try:
            return operation()
        except retry_on as exc:
            last_error = exc
            if attempt >= retry_config.attempts:
                break
            delay = retry_config.delay_for_attempt(attempt)
            retry_after = _retry_after_delay(exc)
            if retry_after is not None:
                delay = max(delay, min(retry_config.max_delay_seconds, retry_after))
            if on_retry is not None:
                on_retry(attempt, exc, delay)
            time.sleep(delay)
    if last_error is None:
        raise RuntimeError("retry operation failed without an exception")
    raise last_error
