"""Local event folder and JPEG burst writer."""

from __future__ import annotations

import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2


class EventWriter:
    def __init__(self, settings: dict[str, Any]) -> None:
        self.settings = settings
        self.base_directory = Path(settings["directory"])
        self._last_event = 0.0
        self._lock = threading.Lock()
        self.last_event: str | None = None

    def save_burst(self, frame) -> bool:
        with self._lock:
            now = time.monotonic()
            if now - self._last_event < self.settings["cooldown_seconds"]:
                return False
            self._last_event = now
        timestamp = datetime.now()
        folder = (
            self.base_directory / timestamp.strftime("%Y-%m-%d") / timestamp.strftime("%H%M%S_%f")
        )
        folder.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(folder / "frame_000.jpg"), frame)
        self.last_event = str(folder)
        threading.Thread(target=self._save_remaining, args=(folder,), daemon=True).start()
        return True

    def _save_remaining(self, folder: Path) -> None:
        # The monitor supplies new frames through this callback after construction.
        for index in range(1, self.settings["burst_frames"]):
            time.sleep(self.settings["burst_interval_seconds"])
            frame = self.frame_supplier() if hasattr(self, "frame_supplier") else None
            if frame is not None:
                cv2.imwrite(str(folder / f"frame_{index:03d}.jpg"), frame)
