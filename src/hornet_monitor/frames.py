"""Small, testable frame transformations used by the capture pipeline."""

from __future__ import annotations


def crop_to_roi(frame, roi: dict[str, int]):
    """Return a copy of the configured rectangle, clamped to the frame bounds."""
    x, y = max(0, roi["x"]), max(0, roi["y"])
    width = min(roi["width"], frame.shape[1] - x)
    height = min(roi["height"], frame.shape[0] - y)
    if width < 1 or height < 1:
        raise ValueError("ROI is outside the frame.")
    return frame[y : y + height, x : x + width].copy()
