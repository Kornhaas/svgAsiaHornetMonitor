"""Optional, rate-limited Telegram notifications for prediction review."""

from __future__ import annotations

import time
import urllib.parse
import urllib.request


class TelegramNotifier:
    def __init__(self, settings: dict, activity_log=None, clock=time.monotonic) -> None:
        self.settings, self.activity_log, self.clock = settings, activity_log, clock
        self.last_sent = 0.0

    def notify(self, prediction: dict) -> bool:
        if not self.settings.get("enabled") or not self._needs_review(prediction):
            return False
        if self.clock() - self.last_sent < self.settings["cooldown_seconds"]:
            return False
        token, chat_id = self.settings.get("bot_token"), self.settings.get("chat_id")
        if not token or not chat_id:
            return False
        text = (
            f"Hornet Monitor: {prediction['label']} ({prediction['confidence']:.0%})\n"
            f"{prediction['image']}"
        )
        request = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode(),
        )
        try:
            with urllib.request.urlopen(request, timeout=10):
                pass
            self.last_sent = self.clock()
            if self.activity_log:
                self.activity_log.record(
                    "telegram_sent", "Telegram review notification sent", details=prediction
                )
            return True
        except OSError as error:
            if self.activity_log:
                self.activity_log.record("telegram_failed", str(error), level="error")
            return False

    def _needs_review(self, prediction: dict) -> bool:
        return (
            prediction["label"] == "vespa_velutina"
            or prediction["confidence"] < self.settings["confidence_threshold"]
        )
