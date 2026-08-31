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
        model_path = self.models_directory / "run" / "weights" / "best.pt"
        if not model_path.exists():
            return
        try:
            from ultralytics import YOLO

            result = YOLO(str(model_path))(image, verbose=False)[0]
            if not len(result.boxes):
                return
            index = int(result.boxes.conf.argmax())
            prediction = {
                "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
                "image": image,
                "label": result.names[int(result.boxes.cls[index])],
                "confidence": float(result.boxes.conf[index]),
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
