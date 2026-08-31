"""Read-only training dataset and model status for the browser UI."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


class TrainingStatus:
    """Summarize locally stored annotations without starting model training."""

    def __init__(self, annotations_file: str | Path, settings: dict[str, Any]) -> None:
        self.annotations_file = Path(annotations_file)
        self.settings = settings

    def overview(self) -> dict[str, Any]:
        annotations = self._annotations()
        reviewed_images = {entry.get("image") for entry in annotations if entry.get("image")}
        labels = Counter(entry.get("label", "unknown") for entry in annotations)
        minimum = self.settings["minimum_annotations"]
        return {
            "state": "not_configured",
            "message": "No model has been trained yet. Keep reviewing images to build the dataset.",
            "reviewed_images": len(reviewed_images),
            "annotations": len(annotations),
            "minimum_annotations": minimum,
            "ready": len(annotations) >= minimum,
            "labels": dict(sorted(labels.items())),
            "schedule": {
                "start_hour": self.settings["start_hour"],
                "stop_hour": self.settings["stop_hour"],
            },
        }

    def _annotations(self) -> list[dict[str, Any]]:
        if not self.annotations_file.exists():
            return []
        with self.annotations_file.open(encoding="utf-8") as annotation_file:
            return [json.loads(line) for line in annotation_file if line.strip()]
