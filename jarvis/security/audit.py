"""Sanitized in-memory audit records and JSON export."""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_SECRET = re.compile(r"(?i)(token|password|secret|api[_-]?key)\s*[:=]\s*[^\s,}]+")


def _sanitize(value: Any) -> Any:
    if isinstance(value, str):
        return _SECRET.sub(r"\1=[REDACTED]", value)[:1000]
    if isinstance(value, dict):
        return {
            str(k): _sanitize(v)
            for k, v in value.items()
            if str(k).casefold().replace("-", "_") not in {"token", "password", "secret", "api_key"}
        }
    if isinstance(value, (list, tuple)):
        return [_sanitize(v) for v in value]
    return value


@dataclass
class AuditLog:
    entries: list[dict[str, Any]] = field(default_factory=list)

    def record(self, action: str, status: str, details: dict[str, Any] | None = None) -> None:
        self.entries.append({"timestamp": round(time.time(), 3), "action": action, "status": status, "details": _sanitize(details or {})})

    def export(self, path: str | Path) -> str:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.entries, indent=2), encoding="utf-8")
        return str(target)
