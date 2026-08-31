"""ROI-only background-subtraction motion detection."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any

import cv2


@dataclass(frozen=True)
class MotionResult:
    detected: bool
    largest_area: float


class MotionDetector:
    def __init__(self, settings: dict[str, Any]) -> None:
        self.settings = settings
        self._background = None
        self._lock = threading.RLock()

    def roi(self) -> dict[str, int]:
        with self._lock:
            return dict(self.settings["roi"])

    def trigger_roi(self) -> dict[str, int]:
        with self._lock:
            return dict(self.settings.get("trigger_roi", self.settings["roi"]))

    def update_roi(
        self, roi: dict[str, int], frame_width: int, frame_height: int
    ) -> dict[str, int]:
        required = ("x", "y", "width", "height")
        if any(key not in roi or not isinstance(roi[key], int) for key in required):
            raise ValueError("ROI requires integer x, y, width, and height values.")
        x, y, width, height = (roi[key] for key in required)
        if (
            x < 0
            or y < 0
            or width < 1
            or height < 1
            or x + width > frame_width
            or y + height > frame_height
        ):
            raise ValueError("ROI must be fully inside the camera image.")
        with self._lock:
            self.settings["roi"] = dict(roi)
            self._background = None
            return self.roi()

    def detect(self, frame) -> MotionResult:
        with self._lock:
            return self._detect(frame)

    def reset(self) -> None:
        with self._lock:
            self._background = None

    def update_trigger_roi(
        self, roi: dict[str, int], frame_width: int, frame_height: int
    ) -> dict[str, int]:
        self.update_roi(self.roi(), frame_width, frame_height)
        required = ("x", "y", "width", "height")
        if any(key not in roi or not isinstance(roi[key], int) for key in required):
            raise ValueError("Trigger ROI requires integer x, y, width, and height values.")
        outer = self.roi()
        if not (
            outer["x"] <= roi["x"]
            and outer["y"] <= roi["y"]
            and roi["x"] + roi["width"] <= outer["x"] + outer["width"]
            and roi["y"] + roi["height"] <= outer["y"] + outer["height"]
        ):
            raise ValueError("Trigger ROI must be fully inside the image ROI.")
        with self._lock:
            self.settings["trigger_roi"] = dict(roi)
            self._background = None
            return self.trigger_roi()

    def _detect(self, frame) -> MotionResult:
        roi = self.settings.get("trigger_roi", self.settings["roi"])
        x, y = max(0, roi["x"]), max(0, roi["y"])
        width = min(roi["width"], frame.shape[1] - x)
        height = min(roi["height"], frame.shape[0] - y)
        if width <= 0 or height <= 0:
            return MotionResult(False, 0)
        crop = frame[y : y + height, x : x + width]
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        blur = self.settings.get("blur_size", 21)
        blur = blur if blur % 2 else blur + 1
        gray = cv2.GaussianBlur(gray, (blur, blur), 0)
        if self._background is None:
            self._background = gray.astype("float")
            return MotionResult(False, 0)
        cv2.accumulateWeighted(gray, self._background, 0.05)
        delta = cv2.absdiff(gray, cv2.convertScaleAbs(self._background))
        _, threshold = cv2.threshold(delta, self.settings["threshold"], 255, cv2.THRESH_BINARY)
        threshold = cv2.dilate(threshold, None, iterations=2)
        contours, _ = cv2.findContours(threshold, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        largest = max((cv2.contourArea(contour) for contour in contours), default=0)
        return MotionResult(largest >= self.settings["min_area"], largest)
