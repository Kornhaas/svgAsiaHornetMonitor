"""Local storage warning and recoverable metadata backup operations."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path


class StorageManager:
    def __init__(
        self,
        settings: dict,
        sources: list[str],
        events_directory: str | None = None,
        annotations_file: str | None = None,
    ) -> None:
        self.settings, self.sources = settings, [Path(source) for source in sources]
        self.events_directory = Path(events_directory) if events_directory else None
        self.annotations_file = Path(annotations_file) if annotations_file else None
        self.last_cleanup: dict | None = None

    def status(self) -> dict:
        usage = shutil.disk_usage(self.settings["directory"])
        free_gb = round(usage.free / 1024**3, 1)
        return {
            "free_gb": free_gb,
            "minimum_free_gb": self.settings["minimum_free_gb"],
            "warning": free_gb < self.settings["minimum_free_gb"],
            "last_cleanup": self.last_cleanup,
        }

    def backup(self) -> str:
        destination = Path(self.settings["backup_directory"])
        destination.mkdir(parents=True, exist_ok=True)
        archive = destination / f"hornet-backup-{datetime.now():%Y%m%d_%H%M%S}"
        with _Backup(archive, self.sources):
            pass
        return str(archive.with_suffix(".zip"))

    def cleanup(self, now: datetime | None = None) -> dict:
        if self.events_directory is None or not self.events_directory.exists():
            self.last_cleanup = {"deleted": 0, "checked_at": datetime.now().isoformat()}
            return self.last_cleanup
        now = now or datetime.now()
        reviewed = self._reviewed_images()
        deleted = 0
        for event in self.events_directory.glob("*/*"):
            if not event.is_dir():
                continue
            image_id = f"{event.parent.name}/{event.name}/frame_000.jpg"
            retention = (
                self.settings["reviewed_retention_days"]
                if image_id in reviewed
                else self.settings["unreviewed_retention_days"]
            )
            age_days = (now - datetime.fromtimestamp(event.stat().st_mtime)).total_seconds() / 86400
            if age_days >= retention:
                shutil.rmtree(event)
                deleted += 1
        self.last_cleanup = {"deleted": deleted, "checked_at": now.isoformat(timespec="seconds")}
        return self.last_cleanup

    def _reviewed_images(self) -> set[str]:
        if self.annotations_file is None or not self.annotations_file.exists():
            return set()
        reviewed = set()
        for line in self.annotations_file.read_text(encoding="utf-8").splitlines():
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("image"):
                reviewed.add(entry["image"])
        return reviewed


class _Backup:
    def __init__(self, archive: Path, sources: list[Path]) -> None:
        self.archive, self.sources = archive, sources

    def __enter__(self):
        import zipfile

        self.zip = zipfile.ZipFile(self.archive.with_suffix(".zip"), "w", zipfile.ZIP_DEFLATED)
        for source in self.sources:
            if source.is_file():
                self.zip.write(source, source.name)
            elif source.is_dir():
                for file in source.rglob("*"):
                    if file.is_file() and not file.is_symlink():
                        self.zip.write(file, source.name / file.relative_to(source))
        return self

    def __exit__(self, *_):
        self.zip.close()
