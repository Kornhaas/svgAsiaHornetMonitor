"""Event-image discovery and annotation storage for the local review gallery."""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from werkzeug.utils import safe_join

ANIMAL_LABELS = frozenset(
    {
        "vespa_velutina",
        "vespa_crabro",
        "wasp",
        "bee",
        "other",
        "goldfly",
        "fleshfly",
        "blue_blowfly",
    }
)
VALID_LABELS = ANIMAL_LABELS | {"empty", "uncertain"}


class Gallery:
    _EVENT_IMAGE_ID = re.compile(r"\d{4}-\d{2}-\d{2}/[0-9_]+/frame_\d+\.jpe?g\Z")

    def __init__(self, events_directory: str | Path, annotations_file: str | Path) -> None:
        self.events_directory = Path(events_directory).resolve()
        self.annotations_file = Path(annotations_file)
        self._lock = threading.RLock()

    def events(self, limit: int = 100) -> list[dict[str, Any]]:
        images = sorted(self.events_directory.glob("*/*/frame_000.jpg"), reverse=True)
        annotations = self._annotations()
        reviewed_images = {annotation.get("image") for annotation in annotations}
        animal_images = {
            annotation.get("image")
            for annotation in annotations
            if annotation.get("label") in ANIMAL_LABELS
        }
        return [self._event(image, reviewed_images, animal_images) for image in images[:limit]]

    def _event(
        self,
        image: Path,
        reviewed_images: set[str | None],
        animal_images: set[str | None],
    ) -> dict[str, Any]:
        frames = [
            frame.relative_to(self.events_directory).as_posix()
            for frame in sorted(image.parent.glob("frame_*.jpg"))
        ]
        return {
            "id": image.parent.relative_to(self.events_directory).as_posix(),
            "image": image.relative_to(self.events_directory).as_posix(),
            "frames": frames,
            "image_count": len(frames),
            "reviewed_frames": [frame for frame in frames if frame in reviewed_images],
            "animal_frames": [frame for frame in frames if frame in animal_images],
            "reviewed": any(frame in reviewed_images for frame in frames),
        }

    def _annotations(self) -> list[dict[str, Any]]:
        if not self.annotations_file.exists():
            return []
        with self.annotations_file.open(encoding="utf-8") as annotations:
            return [json.loads(line) for line in annotations if line.strip()]

    def image_path(self, image_id: str) -> Path:
        if not isinstance(image_id, str) or not self._EVENT_IMAGE_ID.fullmatch(image_id):
            raise ValueError("Invalid event image path.")
        # safe_join is a second, library-provided containment boundary for filesystem access.
        candidate = safe_join(self.events_directory, image_id)
        if candidate is None:
            raise ValueError("Invalid event image path.")
        candidate = Path(candidate)
        if not candidate.is_file():
            raise FileNotFoundError(image_id)
        return candidate

    def annotations_for(self, image_id: str) -> list[dict[str, Any]]:
        self.image_path(image_id)
        return [entry for entry in self._annotations() if entry.get("image") == image_id]

    def annotate(self, annotation: dict[str, Any]) -> dict[str, Any]:
        if "annotations" in annotation:
            items = annotation["annotations"]
            if not isinstance(items, list) or not items:
                raise ValueError("At least one annotation is required.")
            image = self.image_path(annotation["image"])
            validated = [
                self._validate(image, item.get("label"), item.get("box")) for item in items
            ]
            return {
                "image": image.relative_to(self.events_directory).as_posix(),
                "annotations": self._replace(image, validated),
            }
        image = self.image_path(annotation["image"])
        return self._store(
            image, *self._validate(image, annotation.get("label"), annotation.get("box"))
        )

    def _validate(self, image: Path, label: str | None, box: dict[str, int] | None):
        if label not in VALID_LABELS:
            raise ValueError("Unknown label.")
        if label == "empty" and box is None:
            return label, box
        if not isinstance(box, dict) or any(
            not isinstance(box.get(key), int) for key in ("x", "y", "width", "height")
        ):
            raise ValueError("Box requires integer x, y, width, and height values.")
        if box["x"] < 0 or box["y"] < 0 or box["width"] < 1 or box["height"] < 1:
            raise ValueError("Box coordinates must be positive.")
        return label, box

    def _replace(
        self, image: Path, items: list[tuple[str, dict[str, int] | None]]
    ) -> list[dict[str, Any]]:
        image_id = image.relative_to(self.events_directory).as_posix()
        with self._lock:
            entries = [entry for entry in self._annotations() if entry.get("image") != image_id]
            entries.extend(self._entry(image, label, box) for label, box in items)
            self._write_annotations(entries)
        return [entry for entry in entries if entry.get("image") == image_id]

    def _store(self, image: Path, label: str, box: dict[str, int] | None) -> dict[str, Any]:
        entry = self._entry(image, label, box)
        with self._lock:
            self._write_annotations([*self._annotations(), entry])
        return entry

    def _write_annotations(self, entries: list[dict[str, Any]]) -> None:
        self.annotations_file.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=self.annotations_file.parent, delete=False
        ) as temporary:
            for entry in entries:
                temporary.write(json.dumps(entry) + "\n")
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, self.annotations_file)

    def _entry(self, image: Path, label: str, box: dict[str, int] | None) -> dict[str, Any]:
        return {
            "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
            "image": image.relative_to(self.events_directory).as_posix(),
            "label": label,
            "box": box,
        }

    def delete_event(self, event_id: str) -> None:
        event_directory = (self.events_directory / event_id).resolve()
        if event_directory.parent.parent != self.events_directory or not event_directory.is_dir():
            raise ValueError("Invalid event path.")
        shutil.rmtree(event_directory)
        if self.annotations_file.exists():
            prefix = f"{event_id}/"
            with self._lock:
                remaining = [
                    entry
                    for entry in self._annotations()
                    if not entry.get("image", "").startswith(prefix)
                ]
                self._write_annotations(remaining)
