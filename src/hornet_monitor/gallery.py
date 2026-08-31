"""Event-image discovery and annotation storage for the local review gallery."""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any


class Gallery:
    def __init__(self, events_directory: str | Path, annotations_file: str | Path) -> None:
        self.events_directory = Path(events_directory).resolve()
        self.annotations_file = Path(annotations_file)
        self._lock = threading.Lock()

    def events(self, limit: int = 100) -> list[dict[str, Any]]:
        images = sorted(self.events_directory.glob("*/*/frame_000.jpg"), reverse=True)
        return [self._event(image) for image in images[:limit]]

    def _event(self, image: Path) -> dict[str, Any]:
        return {
            "id": image.parent.relative_to(self.events_directory).as_posix(),
            "image": image.relative_to(self.events_directory).as_posix(),
            "image_count": len(list(image.parent.glob("frame_*.jpg"))),
        }

    def image_path(self, image_id: str) -> Path:
        candidate = (self.events_directory / image_id).resolve()
        if self.events_directory not in candidate.parents or candidate.suffix.lower() not in {
            ".jpg",
            ".jpeg",
        }:
            raise ValueError("Invalid event image path.")
        if not candidate.is_file():
            raise FileNotFoundError(image_id)
        return candidate

    def annotate(self, annotation: dict[str, Any]) -> dict[str, Any]:
        image = self.image_path(annotation["image"])
        label, box = annotation.get("label"), annotation.get("box")
        labels = {"vespa_velutina", "vespa_crabro", "wasp", "bee", "other", "empty", "uncertain"}
        if label not in labels:
            raise ValueError("Unknown label.")
        if label == "empty" and box is None:
            return self._store(image, label, box)
        if not isinstance(box, dict) or any(
            not isinstance(box.get(key), int) for key in ("x", "y", "width", "height")
        ):
            raise ValueError("Box requires integer x, y, width, and height values.")
        if box["x"] < 0 or box["y"] < 0 or box["width"] < 1 or box["height"] < 1:
            raise ValueError("Box coordinates must be positive.")
        return self._store(image, label, box)

    def _store(self, image: Path, label: str, box: dict[str, int] | None) -> dict[str, Any]:
        entry = {
            "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
            "image": image.relative_to(self.events_directory).as_posix(),
            "label": label,
            "box": box,
        }
        with self._lock:
            self.annotations_file.parent.mkdir(parents=True, exist_ok=True)
            with self.annotations_file.open("a", encoding="utf-8") as annotations:
                annotations.write(json.dumps(entry) + "\n")
        return entry
