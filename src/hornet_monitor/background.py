"""Reference-background capture and conservative OpenCV object proposals."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import cv2


class BackgroundReference:
    def __init__(self, image_file: str, metadata_file: str, minimum_area: int) -> None:
        self.image_file = Path(image_file)
        self.metadata_file = Path(metadata_file)
        self.minimum_area = minimum_area

    def status(self) -> dict:
        if not self.metadata_file.exists():
            return {"available": False, "updated_at": None}
        return {"available": self.image_file.exists(), **json.loads(self.metadata_file.read_text())}

    def save(self, frame) -> dict:
        self.image_file.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(self.image_file), frame):
            raise ValueError("Could not write the background image.")
        details = {
            "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "width": frame.shape[1],
            "height": frame.shape[0],
        }
        self.metadata_file.write_text(json.dumps(details), encoding="utf-8")
        return {"available": True, **details}

    def proposals(self, frame) -> list[dict[str, int]]:
        reference = cv2.imread(str(self.image_file))
        if reference is None:
            return []
        if reference.shape[:2] != frame.shape[:2]:
            raise ValueError(
                "Background image size differs from the current ROI. Update the background."
            )
        difference = cv2.absdiff(
            cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY)
        )
        _, mask = cv2.threshold(cv2.GaussianBlur(difference, (7, 7), 0), 35, 255, cv2.THRESH_BINARY)
        mask = cv2.morphologyEx(
            mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        )
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return [
            {"x": x, "y": y, "width": width, "height": height}
            for contour in contours
            for x, y, width, height in [cv2.boundingRect(contour)]
            if width * height >= self.minimum_area
        ]
