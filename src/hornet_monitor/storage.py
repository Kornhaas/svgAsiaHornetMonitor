"""Local storage warning and recoverable metadata backup operations."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


class StorageManager:
    def __init__(self, settings: dict, sources: list[str]) -> None:
        self.settings, self.sources = settings, [Path(source) for source in sources]

    def status(self) -> dict:
        usage = shutil.disk_usage(self.settings["directory"])
        free_gb = round(usage.free / 1024**3, 1)
        return {
            "free_gb": free_gb,
            "minimum_free_gb": self.settings["minimum_free_gb"],
            "warning": free_gb < self.settings["minimum_free_gb"],
        }

    def backup(self) -> str:
        destination = Path(self.settings["backup_directory"])
        destination.mkdir(parents=True, exist_ok=True)
        archive = destination / f"hornet-backup-{datetime.now():%Y%m%d_%H%M%S}"
        with _Backup(archive, self.sources):
            pass
        return str(archive.with_suffix(".zip"))


class _Backup:
    def __init__(self, archive: Path, sources: list[Path]) -> None:
        self.archive, self.sources = archive, sources

    def __enter__(self):
        import zipfile

        self.zip = zipfile.ZipFile(self.archive.with_suffix(".zip"), "w", zipfile.ZIP_DEFLATED)
        for source in self.sources:
            if source.is_file():
                self.zip.write(source, source.name)
        return self

    def __exit__(self, *_):
        self.zip.close()
