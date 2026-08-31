"""Bounded background YOLO training worker with durable status."""

from __future__ import annotations

import json
import multiprocessing
from datetime import datetime, timedelta
from pathlib import Path

from .dataset import DatasetExporter


def _train(dataset_yaml: str, settings: dict, output: str) -> None:
    from ultralytics import YOLO

    YOLO(settings["model_name"]).train(
        data=dataset_yaml,
        epochs=settings["epochs"],
        imgsz=settings["image_size"],
        device="cpu",
        project=output,
        name="run",
        exist_ok=True,
        workers=0,
    )


class TrainingManager:
    def __init__(self, exporter: DatasetExporter, settings: dict, activity_log=None) -> None:
        self.exporter, self.settings, self.activity_log = exporter, settings, activity_log
        self.state_file = Path(settings["models_directory"]) / "status.json"
        self.process: multiprocessing.Process | None = None
        self.deadline: datetime | None = None

    def status(self) -> dict:
        state = {"state": "idle", "message": "No training run has started."}
        if self.state_file.exists():
            state.update(json.loads(self.state_file.read_text(encoding="utf-8")))
        if self.process and self.process.is_alive():
            if self.deadline and datetime.now() >= self.deadline:
                self.process.terminate()
                self._save(
                    {
                        "state": "stopped",
                        "message": "Training stopped at the configured morning deadline.",
                    }
                )
            else:
                state.update(
                    {
                        "state": "running",
                        "deadline": self.deadline.isoformat() if self.deadline else None,
                    }
                )
        elif self.process and state.get("state") == "running":
            state = self._save(
                {
                    "state": "completed" if self.process.exitcode == 0 else "failed",
                    "message": "Training completed."
                    if self.process.exitcode == 0
                    else "Training worker exited with an error.",
                    "model": str(self.models_path()),
                }
            )
        return state

    def models_path(self) -> Path:
        return Path(self.settings["models_directory"]) / "run" / "weights" / "best.pt"

    def start(self) -> dict:
        if self.process and self.process.is_alive():
            return self.status()
        summary = self.exporter.summary()
        if summary["boxes"] < self.settings["minimum_annotations"]:
            return self._save(
                {"state": "waiting", "message": "More labelled boxes are required.", **summary}
            )
        dataset = self.exporter.export()
        now = datetime.now()
        stop = now.replace(hour=self.settings["stop_hour"], minute=0, second=0, microsecond=0)
        self.deadline = stop if stop > now else stop + timedelta(days=1)
        self.process = multiprocessing.Process(
            target=_train,
            args=(
                str(Path(dataset["directory"]) / "dataset.yaml"),
                self.settings,
                self.settings["models_directory"],
            ),
            daemon=True,
        )
        self.process.start()
        return self._save(
            {
                "state": "running",
                "message": "Training started.",
                "dataset": dataset,
                "started_at": now.isoformat(),
                "deadline": self.deadline.isoformat(),
            }
        )

    def _save(self, state: dict) -> dict:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
        return state
