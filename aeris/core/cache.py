from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def stable_cache_key(namespace: str, payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    safe_namespace = namespace.replace("\\", "_").replace("/", "_").replace(":", "_")
    return f"{safe_namespace}-{digest}"


@dataclass(frozen=True, slots=True)
class CacheManager:
    root: Path

    def __post_init__(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for_key(self, namespace: str, key_payload: dict[str, Any], suffix: str = ".json") -> Path:
        key = stable_cache_key(namespace, key_payload)
        namespace_dir = self.root / namespace
        namespace_dir.mkdir(parents=True, exist_ok=True)
        return namespace_dir / f"{key}{suffix}"

    def load_json(self, namespace: str, key_payload: dict[str, Any]) -> dict[str, Any] | list[Any] | None:
        path = self.path_for_key(namespace, key_payload)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def save_json(self, namespace: str, key_payload: dict[str, Any], payload: dict[str, Any] | list[Any]) -> Path:
        path = self.path_for_key(namespace, key_payload)
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    def bytes_path(self, namespace: str, key_payload: dict[str, Any], suffix: str) -> Path:
        return self.path_for_key(namespace, key_payload, suffix=suffix)

    def exists(self, namespace: str, key_payload: dict[str, Any], suffix: str = ".json") -> bool:
        return self.path_for_key(namespace, key_payload, suffix=suffix).exists()
