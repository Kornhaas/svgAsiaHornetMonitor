"""ROI-only background-subtraction motion detection."""

from __future__ import annotations

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

    def detect(self, frame) -> MotionResult:
        roi = self.settings["roi"]
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
