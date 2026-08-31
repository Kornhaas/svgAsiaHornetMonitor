"""Asynchronous inference isolated from camera and event writing."""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path


class Predictor:
    def __init__(
        self, models_directory: str, predictions_file: str, notifier=None, activity_log=None
    ) -> None:
        self.models_directory, self.predictions_file = (
            Path(models_directory),
            Path(predictions_file),
        )
        self.notifier, self.activity_log = notifier, activity_log

    def submit(self, image: str) -> None:
        threading.Thread(target=self._predict, args=(image,), daemon=True).start()

    def _predict(self, image: str) -> None:
        model_path = self._model_path()
        if model_path is None:
            return
        try:
            from ultralytics import YOLO

            result = YOLO(str(model_path))(image, verbose=False)[0]
            if not len(result.boxes):
                return
            detections = [
                {
                    "label": result.names[int(result.boxes.cls[index])],
                    "confidence": float(result.boxes.conf[index]),
                }
                for index in range(len(result.boxes))
            ]
            best = max(detections, key=lambda detection: detection["confidence"])
            prediction = {
                "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
                "image": image,
                **best,
                "detections": detections,
            }
            self.predictions_file.parent.mkdir(parents=True, exist_ok=True)
            with self.predictions_file.open("a", encoding="utf-8") as file:
                file.write(json.dumps(prediction) + "\n")
            if self.notifier:
                self.notifier.notify(prediction)
            if self.activity_log:
                self.activity_log.record(
                    "prediction", "Model prediction completed", details=prediction
                )
        except (ImportError, OSError, RuntimeError) as error:
            if self.activity_log:
                self.activity_log.record("prediction_failed", str(error), level="error")

    def history(self, limit: int = 50) -> list[dict]:
        if not self.predictions_file.exists():
            return []
        lines = self.predictions_file.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in reversed(lines[-limit:]) if line]

    def _model_path(self) -> Path | None:
        latest = self.models_directory / "latest.json"
        if latest.exists():
            try:
                model = Path(json.loads(latest.read_text(encoding="utf-8"))["model"])
                if model.is_file():
                    return model
            except (json.JSONDecodeError, KeyError):
                pass
        legacy = self.models_directory / "run" / "weights" / "best.pt"
        return legacy if legacy.exists() else None
