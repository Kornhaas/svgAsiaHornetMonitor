"""Camera-image brightness based night-mode state machine."""

from __future__ import annotations

import time

import cv2


class NightMode:
    PREVIEW_DARK_THRESHOLD = 30

    def __init__(self, settings: dict, clock=time.monotonic) -> None:
        self.settings = settings
        self.clock = clock
        self.dark_since: float | None = None
        self.active = False
        self.brightness: float | None = None

    def observe(self, frame) -> bool | None:
        if not self.settings.get("enabled", True):
            return None
        self.brightness = round(float(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).mean()), 1)
        now = self.clock()
        if self.active:
            if self.brightness >= self.settings["bright_threshold"]:
                self.active, self.dark_since = False, None
                return False
            return None
        if self.brightness < self.settings["dark_threshold"]:
            if self.dark_since is None:
                self.dark_since = now
            if now - self.dark_since >= self.settings["dark_seconds"]:
                self.active = True
                return True
        else:
            self.dark_since = None
        return None

    def status(self) -> dict:
        return {
            "active": self.active,
            "brightness": self.brightness,
            "dark_seconds": self.settings["dark_seconds"],
            "preview_disabled": self.brightness is not None
            and self.brightness < self.PREVIEW_DARK_THRESHOLD,
            "pending": self.dark_since is not None and not self.active,
        }
