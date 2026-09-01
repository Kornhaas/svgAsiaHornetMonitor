"""Asynchronous inference isolated from camera and event writing."""

from __future__ import annotations

import json
import multiprocessing
import os
import threading
from datetime import datetime
from pathlib import Path


def _model_path(models_directory: Path) -> Path | None:
    latest = models_directory / "latest.json"
    if latest.exists():
        try:
            model = Path(json.loads(latest.read_text(encoding="utf-8"))["model"])
            if model.is_file():
                return model
        except (json.JSONDecodeError, KeyError):
            pass
    legacy = models_directory / "run" / "weights" / "best.pt"
    return legacy if legacy.exists() else None


def _predict_image(
    models_directory: str,
    predictions_file: str,
    image: str,
    telegram_settings: dict | None,
    activity_file: str | None,
) -> None:
    """Run native ML code outside the monitor process."""
    model_path = _model_path(Path(models_directory))
    if model_path is None:
        return
    try:
        os.environ.setdefault("OMP_NUM_THREADS", "1")
        os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
        try:
            os.nice(10)
        except OSError:
            pass
        import cv2
        import numpy as np
        import torch
        from ultralytics import YOLO
        from ultralytics.utils.nms import non_max_suppression

        cv2.setNumThreads(1)
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
        captured = cv2.imread(image)
        if captured is None:
            raise ValueError("Event image could not be read.")
        resized = cv2.resize(captured, (640, 640))
        tensor = (
            torch.from_numpy(np.ascontiguousarray(resized[..., ::-1].transpose(2, 0, 1))).float()
            / 255
        )
        model = YOLO(str(model_path))
        raw = model.model(tensor.unsqueeze(0))
        boxes = non_max_suppression(raw, conf_thres=0.25)[0]
        if not len(boxes):
            return
        detections = [
            {
                "label": model.names[int(box[5])],
                "confidence": float(box[4]),
            }
            for box in boxes
        ]
        best = max(detections, key=lambda detection: detection["confidence"])
        prediction = {
            "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
            "image": image,
            **best,
            "detections": detections,
        }
        destination = Path(predictions_file)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("a", encoding="utf-8") as file:
            file.write(json.dumps(prediction) + "\n")
        if activity_file:
            from .activity import ActivityLog

            activity_log = ActivityLog(activity_file)
            activity_log.record("prediction", "Model prediction completed", details=prediction)
            if telegram_settings:
                from .notifier import TelegramNotifier

                TelegramNotifier(telegram_settings, activity_log).notify(prediction)
    except (ImportError, OSError, RuntimeError, ValueError, TypeError) as error:
        if activity_file:
            from .activity import ActivityLog

            ActivityLog(activity_file).record("prediction_failed", str(error), level="error")


class Predictor:
    def __init__(
        self, models_directory: str, predictions_file: str, notifier=None, activity_log=None
    ) -> None:
        self.models_directory, self.predictions_file = (
            Path(models_directory),
            Path(predictions_file),
        )
        self.notifier, self.activity_log = notifier, activity_log
        self._process: multiprocessing.Process | None = None
        self._lock = threading.Lock()

    def submit(self, image: str) -> bool:
        """Queue one isolated inference; retain camera stability if native ML crashes."""
        if self._model_path() is None:
            return False
        with self._lock:
            self.reap()
            if self._process and self._process.is_alive():
                if self.activity_log:
                    self.activity_log.record(
                        "prediction_skipped",
                        "Prediction skipped because another inference is still running.",
                    )
                return False
            context = multiprocessing.get_context("spawn")
            self._process = context.Process(
                target=_predict_image,
                args=(
                    str(self.models_directory),
                    str(self.predictions_file),
                    image,
                    self.notifier.settings if self.notifier else None,
                    str(self.activity_log.path) if self.activity_log else None,
                ),
                daemon=True,
            )
            self._process.start()
        return True

    def reap(self) -> None:
        """Record a failed child process without ever terminating the monitor."""
        if self._process is None or self._process.is_alive():
            return
        self._process.join()
        exitcode = self._process.exitcode
        self._process.close()
        self._process = None
        if exitcode not in (0, None) and self.activity_log:
            self.activity_log.record(
                "prediction_failed",
                "Inference worker stopped unexpectedly; camera monitoring continues.",
                level="error",
                details={"exit_code": exitcode},
            )

    def _predict(self, image: str) -> None:
        _predict_image(
            str(self.models_directory),
            str(self.predictions_file),
            image,
            self.notifier.settings if self.notifier else None,
            str(self.activity_log.path) if self.activity_log else None,
        )

    def history(self, limit: int = 50) -> list[dict]:
        if not self.predictions_file.exists():
            return []
        lines = self.predictions_file.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in reversed(lines[-limit:]) if line]

    def _model_path(self) -> Path | None:
        return _model_path(self.models_directory)
