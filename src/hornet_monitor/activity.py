"""Persistent, lightweight activity history for the local web interface."""

from __future__ import annotations

import json
import threading
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any


class ActivityLog:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()

    def record(
        self, event: str, message: str, level: str = "info", details: dict[str, Any] | None = None
    ) -> None:
        entry = {
            "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
            "event": event,
            "message": message,
            "level": level,
            "details": details or {},
        }
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as activity_file:
                activity_file.write(json.dumps(entry) + "\n")

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        with self._lock:
            with self.path.open(encoding="utf-8") as activity_file:
                lines = deque(activity_file, maxlen=limit)
        return [json.loads(line) for line in reversed(lines) if line.strip()]
