"""Read-only active-learning feedback and deployment-gate metrics."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .gallery import ANIMAL_LABELS


class ActiveLearningStatus:
    """Derive auditable review and confidence evidence from local JSONL files."""

    def __init__(self, annotations_file: str | Path, predictions_file: str | Path, settings: dict):
        self.annotations_file = Path(annotations_file)
        self.predictions_file = Path(predictions_file)
        self.settings = settings

    def overview(self) -> dict[str, Any]:
        annotations = self._read(self.annotations_file)
        predictions = [
            prediction
            for prediction in self._read(self.predictions_file)
            if prediction.get("label") in ANIMAL_LABELS and prediction.get("best_in_burst", True)
        ]
        latest_annotation = {
            entry["image"]: entry for entry in annotations if isinstance(entry.get("image"), str)
        }
        outcomes = Counter()
        per_model: dict[str, Counter] = defaultdict(Counter)
        calibration: dict[str, list[dict[str, Any]]] = defaultdict(list)
        brightness: list[float] = []
        for prediction in predictions:
            model = prediction.get("model_version") or "unknown"
            annotation = latest_annotation.get(prediction.get("image"))
            outcome = self._outcome(prediction, annotation)
            outcomes[outcome] += 1
            per_model[model][outcome] += 1
            if isinstance(prediction.get("brightness"), (int, float)):
                brightness.append(float(prediction["brightness"]))
            if outcome != "pending":
                calibration[prediction["label"]].append(
                    {
                        "confidence": float(prediction["confidence"]),
                        "correct": outcome == "accepted",
                    }
                )
        class_counts = Counter(
            entry.get("label") for entry in annotations if entry.get("label") in ANIMAL_LABELS
        )
        gates = {label: self._gate(label, calibration[label]) for label in sorted(ANIMAL_LABELS)}
        return {
            "predictions": len(predictions),
            "feedback": dict(outcomes),
            "models": {model: dict(counts) for model, counts in sorted(per_model.items())},
            "calibration": {label: self._calibration(rows) for label, rows in calibration.items()},
            "class_imbalance": dict(sorted(class_counts.items())),
            "underrepresented": [
                label
                for label, count in class_counts.items()
                if count < self.settings["target_per_class"]
            ],
            "brightness": self._brightness(brightness),
            "auto_accept": {
                "enabled": self.settings["auto_accept_enabled"],
                "gates": gates,
                "message": "Automatic acceptance is disabled until explicitly enabled."
                if not self.settings["auto_accept_enabled"]
                else "Only classes passing their evidence gate may be accepted automatically.",
            },
        }

    def automatic_candidates(self) -> list[dict]:
        """Return only new predictions that meet the explicit evidence gate.

        This is intentionally empty under the checked-in default policy. Callers still own
        annotation persistence so no worker process writes training labels directly.
        """
        if not self.settings["auto_accept_enabled"]:
            return []
        annotations = self._read(self.annotations_file)
        reviewed = {entry.get("image") for entry in annotations}
        overview = self.overview()
        candidates = []
        for prediction in self._read(self.predictions_file):
            label = prediction.get("label")
            if (
                prediction.get("best_in_burst", True)
                and prediction.get("image") not in reviewed
                and label in ANIMAL_LABELS
                and prediction.get("confidence", 0) >= self.settings["auto_accept_confidence"]
                and overview["auto_accept"]["gates"].get(label, {}).get("permitted")
                and isinstance(prediction.get("box"), dict)
            ):
                candidates.append(prediction)
        return candidates

    def _gate(self, label: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
        eligible = [
            row for row in rows if row["confidence"] >= self.settings["auto_accept_confidence"]
        ]
        precision = sum(row["correct"] for row in eligible) / len(eligible) if eligible else 0.0
        permitted = (
            label in self.settings["auto_accept_labels"]
            and len(eligible) >= self.settings["auto_accept_min_samples"]
            and precision >= self.settings["auto_accept_min_precision"]
        )
        return {
            "samples": len(eligible),
            "precision": round(precision, 3),
            "permitted": permitted,
        }

    @staticmethod
    def _outcome(prediction: dict, annotation: dict | None) -> str:
        if annotation is None:
            return "pending"
        if annotation.get("source") == "model_confirmed" and annotation.get(
            "prediction_id"
        ) == prediction.get("id"):
            return "accepted"
        if annotation.get("label") == "empty":
            return "empty"
        return "corrected"

    @staticmethod
    def _calibration(rows: list[dict[str, Any]]) -> dict[str, Any]:
        correct = sum(row["correct"] for row in rows)
        return {
            "samples": len(rows),
            "precision": round(correct / len(rows), 3) if rows else 0.0,
        }

    @staticmethod
    def _brightness(values: list[float]) -> dict[str, float | int | None]:
        if not values:
            return {"samples": 0, "mean": None, "range": None}
        return {
            "samples": len(values),
            "mean": round(sum(values) / len(values), 1),
            "range": round(max(values) - min(values), 1),
        }

    @staticmethod
    def _read(path: Path) -> list[dict]:
        if not path.exists():
            return []
        records = []
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                records.append(value)
        return records
