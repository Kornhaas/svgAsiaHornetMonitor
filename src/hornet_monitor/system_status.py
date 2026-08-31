"""Small, dependency-free device health snapshot for the local status UI."""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def snapshot(path: str) -> dict:
    disk = shutil.disk_usage(Path(path).resolve())
    memory = _memory()
    return {
        "disk_free_gb": round(disk.free / 1024**3, 1),
        "disk_total_gb": round(disk.total / 1024**3, 1),
        "cpu_load_1m": round(os.getloadavg()[0], 2) if hasattr(os, "getloadavg") else None,
        "memory_used_percent": memory,
    }


def _memory() -> float | None:
    meminfo = Path("/proc/meminfo")
    if not meminfo.exists():
        return None
    values = dict(line.split(":", 1) for line in meminfo.read_text().splitlines() if ":" in line)
    total = int(values["MemTotal"].split()[0])
    available = int(values["MemAvailable"].split()[0])
    return round((1 - available / total) * 100, 1)
