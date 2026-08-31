"""Controlled repository updates for a systemd-managed monitor."""

from __future__ import annotations

import subprocess
import threading
from pathlib import Path


class UpdateManager:
    def __init__(self, settings, activity_log) -> None:
        self.settings = settings
        self.activity_log = activity_log
        self.repository = Path(settings.get("repository", ".")).resolve()
        self._lock = threading.Lock()
        self._state = {"state": "idle", "message": "No update check has been run."}

    def _git(self, *arguments: str) -> str:
        return subprocess.check_output(["git", *arguments], cwd=self.repository, text=True).strip()

    def check(self) -> dict:
        if not self.settings.get("enabled", False):
            return {"state": "disabled", "message": "Web updates are not configured."}
        try:
            self._git("fetch", "--quiet")
            current = self._git("rev-parse", "--short", "HEAD")
            pending = int(self._git("rev-list", "--count", "HEAD..@{upstream}"))
            self._state = {
                "state": "available" if pending else "current",
                "current": current,
                "pending": pending,
            }
        except (OSError, ValueError, subprocess.SubprocessError):
            self._state = {"state": "error", "message": "Update check failed."}
        return dict(self._state)

    def install(self) -> dict:
        if not self.settings.get("enabled", False):
            return {"state": "disabled", "message": "Web updates are not configured."}
        if self._lock.locked():
            return {"state": "running", "message": "An update is already running."}
        threading.Thread(target=self._install, name="repository-update", daemon=True).start()
        return {
            "state": "running",
            "message": "Update started; the monitor will restart if successful.",
        }

    def _install(self) -> None:
        with self._lock:
            self._state = {"state": "running", "message": "Downloading and installing update."}
            self.activity_log.record("update_started", "Web update started")
            try:
                subprocess.run(["git", "pull", "--ff-only"], cwd=self.repository, check=True)
                subprocess.run(
                    [self.settings["uv_binary"], "sync", "--locked", "--no-dev"],
                    cwd=self.repository,
                    check=True,
                )
                self.activity_log.record("update_installed", "Update installed; restarting monitor")
                self._state = {
                    "state": "restarting",
                    "message": "Update installed; restarting monitor.",
                }
                subprocess.Popen(["sudo", "-n", "systemctl", "restart", self.settings["service"]])
            except (OSError, subprocess.SubprocessError):
                self._state = {"state": "error", "message": "Update installation failed."}
                self.activity_log.record("update_failed", self._state["message"], level="error")
