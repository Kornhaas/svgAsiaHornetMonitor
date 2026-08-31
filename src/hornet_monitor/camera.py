"""Threaded OpenCV camera capture shared by monitoring and browser clients."""

from __future__ import annotations

import threading
import time
from typing import Any

import cv2


class Camera:
    def __init__(self, settings: dict[str, Any]) -> None:
        self.settings = settings
        self._capture: cv2.VideoCapture | None = None
        self._frame = None
        self._lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None
        self.error: str | None = None
        self._last_open_attempt = 0.0

    def start(self) -> None:
        if not self._open():
            return
        self._running = True
        self._thread = threading.Thread(target=self._read_frames, name="camera", daemon=True)
        self._thread.start()

    def _open(self) -> bool:
        device = self.settings["device"]
        if isinstance(device, str) and device.isdigit():
            device = int(device)
        self._capture = cv2.VideoCapture(device, cv2.CAP_V4L2)
        self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.settings["width"])
        self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.settings["height"])
        self._capture.set(cv2.CAP_PROP_FPS, self.settings["fps"])
        if self.settings.get("mjpeg", True):
            self._capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        if not self._capture.isOpened():
            self.error = f"Camera {device!r} could not be opened."
            self._capture.release()
            self._capture = None
            return False
        return True

    def _read_frames(self) -> None:
        while self._running:
            if self._capture is None:
                if time.monotonic() - self._last_open_attempt >= self.settings.get(
                    "reconnect_seconds", 5
                ):
                    self._last_open_attempt = time.monotonic()
                    self._open()
                time.sleep(0.2)
                continue
            ok, frame = self._capture.read()
            if not ok:
                self.error = "Could not read a frame from the camera."
                if time.monotonic() - self._last_open_attempt >= self.settings.get(
                    "reconnect_seconds", 5
                ):
                    self._last_open_attempt = time.monotonic()
                    self._capture.release()
                    self._open()
                time.sleep(0.2)
                continue
            with self._lock:
                self._frame = frame
            self.error = None

    def get_frame(self):
        with self._lock:
            return None if self._frame is None else self._frame.copy()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        if self._capture:
            self._capture.release()
