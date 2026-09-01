"""Asynchronous inference isolated from camera and event writing."""

from __future__ import annotations

import json
import multiprocessing
import os
import threading
import uuid
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


def _model_version(models_directory: Path, model_path: Path) -> str | None:
    """Return the active manifest version when it belongs to the loaded model."""
    latest = models_directory / "latest.json"
    if not latest.exists():
        return None
    try:
        manifest = json.loads(latest.read_text(encoding="utf-8"))
        if Path(manifest["model"]).resolve() == model_path.resolve():
            version = manifest.get("version")
            return version if isinstance(version, str) else None
    except (json.JSONDecodeError, KeyError, OSError):
        return None
    return None


def _predict_images(
    models_directory: str,
    predictions_file: str,
    images: list[tuple[str, str | None]],
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
        model = YOLO(str(model_path))
        predictions = []
        for image, image_id in images:
            captured = cv2.imread(image)
            if captured is None:
                continue
            resized = cv2.resize(captured, (640, 640))
            tensor = (
                torch.from_numpy(
                    np.ascontiguousarray(resized[..., ::-1].transpose(2, 0, 1))
                ).float()
                / 255
            )
            boxes = non_max_suppression(model.model(tensor.unsqueeze(0)), conf_thres=0.25)[0]
            if not len(boxes):
                continue
            height, width = captured.shape[:2]
            scale_x, scale_y = width / 640, height / 640
            detections = []
            for box in boxes:
                left, top, right, bottom = (float(value) for value in box[:4])
                x = max(0, min(width - 1, round(left * scale_x)))
                y = max(0, min(height - 1, round(top * scale_y)))
                right = max(x + 1, min(width, round(right * scale_x)))
                bottom = max(y + 1, min(height, round(bottom * scale_y)))
                detections.append(
                    {
                        "label": model.names[int(box[5])],
                        "confidence": float(box[4]),
                        "box": {"x": x, "y": y, "width": right - x, "height": bottom - y},
                    }
                )
            best = max(detections, key=lambda detection: detection["confidence"])
            predictions.append(
                {
                    "id": uuid.uuid4().hex,
                    "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
                    "image": image_id or image,
                    "model_version": _model_version(Path(models_directory), model_path),
                    "brightness": round(
                        float(cv2.cvtColor(captured, cv2.COLOR_BGR2GRAY).mean()), 1
                    ),
                    **best,
                    "detections": detections,
                }
            )
        if not predictions:
            return
        best_prediction = max(predictions, key=lambda prediction: prediction["confidence"])
        for prediction in predictions:
            prediction["best_in_burst"] = prediction is best_prediction
        destination = Path(predictions_file)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("a", encoding="utf-8") as file:
            file.writelines(json.dumps(prediction) + "\n" for prediction in predictions)
        if activity_file:
            from .activity import ActivityLog

            activity_log = ActivityLog(activity_file)
            activity_log.record("prediction", "Model prediction completed", details=best_prediction)
            if telegram_settings:
                from .notifier import TelegramNotifier

                TelegramNotifier(telegram_settings, activity_log).notify(best_prediction)
    except (ImportError, OSError, RuntimeError, ValueError, TypeError) as error:
        if activity_file:
            from .activity import ActivityLog

            ActivityLog(activity_file).record("prediction_failed", str(error), level="error")


def _predict_image(
    models_directory: str,
    predictions_file: str,
    image: str,
    image_id: str | None,
    telegram_settings: dict | None,
    activity_file: str | None,
) -> None:
    """Compatibility wrapper for one-frame inference."""
    _predict_images(
        models_directory,
        predictions_file,
        [(image, image_id)],
        telegram_settings,
        activity_file,
    )


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

    def submit(self, image: str, image_id: str | None = None) -> bool:
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
                    image_id,
                    self.notifier.settings if self.notifier else None,
                    str(self.activity_log.path) if self.activity_log else None,
                ),
                daemon=True,
            )
            self._process.start()
        return True

    def submit_burst(self, images: list[tuple[str, str]]) -> bool:
        """Queue every completed burst frame in one isolated model-load cycle."""
        if not images or self._model_path() is None:
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
                target=_predict_images,
                args=(
                    str(self.models_directory),
                    str(self.predictions_file),
                    images,
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

    def _predict(self, image: str, image_id: str | None = None) -> None:
        _predict_image(
            str(self.models_directory),
            str(self.predictions_file),
            image,
            image_id,
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
