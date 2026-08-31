"""Read-only training dataset and model status for the browser UI."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


class TrainingStatus:
    """Summarize locally stored annotations without starting model training."""

    def __init__(
        self, annotations_file: str | Path, settings: dict[str, Any], trainer=None
    ) -> None:
        self.annotations_file = Path(annotations_file)
        self.settings = settings
        self.trainer = trainer

    def overview(self) -> dict[str, Any]:
        annotations = self._annotations()
        reviewed_images = {entry.get("image") for entry in annotations if entry.get("image")}
        labels = Counter(entry.get("label", "unknown") for entry in annotations)
        minimum = self.settings["minimum_annotations"]
        training = self.trainer.status() if self.trainer else {}
        return {
            "state": training.get("state", "not_configured"),
            "message": training.get(
                "message",
                "No model has been trained yet. Keep reviewing images to build the dataset.",
            ),
            "reviewed_images": len(reviewed_images),
            "annotations": len(annotations),
            "minimum_annotations": minimum,
            "ready": len(annotations) >= minimum,
            "labels": dict(sorted(labels.items())),
            "dataset": self.trainer.exporter.summary() if self.trainer else {},
            "schedule": {
                "start_hour": self.settings["start_hour"],
                "stop_hour": self.settings["stop_hour"],
            },
            "run": training,
            "models": self.trainer.model_versions() if self.trainer else [],
        }

    def _annotations(self) -> list[dict[str, Any]]:
        if not self.annotations_file.exists():
            return []
        with self.annotations_file.open(encoding="utf-8") as annotation_file:
            return [json.loads(line) for line in annotation_file if line.strip()]
