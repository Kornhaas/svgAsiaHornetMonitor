"""Bounded background YOLO training worker with durable model versions."""

from __future__ import annotations

import csv
import faulthandler
import json
import multiprocessing
import os
import re
import signal
from datetime import datetime, timedelta
from pathlib import Path

from .dataset import DatasetExporter


def _train(dataset_yaml: str, settings: dict, output: str, version: str) -> None:
    # The training worker is deliberately isolated. Keep a Python traceback in
    # the service journal if an ARM native extension terminates it with SIGILL.
    faulthandler.enable(all_threads=True)
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    import torch
    from ultralytics import YOLO
    from ultralytics.models.yolo.detect.train import DetectionTrainer

    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        # The spawned Pi worker is fresh. This keeps unit-test and embedded use
        # safe if another component configured inter-op threads beforehand.
        pass

    class PiDetectionTrainer(DetectionTrainer):
        """Avoid model profiling, which is unsafe in the target ARM wheel."""

        def get_model(self, cfg=None, weights=None, verbose=True):
            return super().get_model(cfg=cfg, weights=weights, verbose=False)

    YOLO(settings["model_name"]).train(
        data=dataset_yaml,
        epochs=settings["epochs"],
        imgsz=settings["image_size"],
        batch=settings.get("batch", 1),
        device="cpu",
        project=output,
        name=version,
        exist_ok=False,
        workers=0,
        cache=False,
        # Ultralytics' automatic AMP check invokes its high-level inference path,
        # which is not stable with the ARM PyTorch build used on the Pi. Training
        # is CPU-only here, so AMP offers no benefit and must stay disabled.
        amp=False,
        trainer=PiDetectionTrainer,
    )


class TrainingManager:
    _VERSION = re.compile(r"\d{8}_\d{6}")

    def __init__(self, exporter: DatasetExporter, settings: dict, activity_log=None) -> None:
        self.exporter, self.settings, self.activity_log = exporter, settings, activity_log
        self.models_directory = Path(settings["models_directory"]).resolve()
        self.state_file = self.models_directory / "status.json"
        self.latest_file = self.models_directory / "latest.json"
        # PyTorch cannot safely initialize CPU kernels in a forked child of the
        # multi-threaded monitor. Use a clean interpreter, like Predictor does.
        self.process_context = multiprocessing.get_context("spawn")
        self.process: multiprocessing.Process | None = None
        self.deadline: datetime | None = None
        self._automatic_window_date = None

    def status(self) -> dict:
        state = {"state": "idle", "message": "No training run has started."}
        if self.state_file.exists():
            state.update(json.loads(self.state_file.read_text(encoding="utf-8")))
        if self.process and self.process.is_alive():
            if self.deadline and datetime.now() >= self.deadline:
                self.process.terminate()
                state = self._save(
                    {
                        **state,
                        "state": "stopped",
                        "message": "Training stopped at the configured morning deadline.",
                        "finished_at": datetime.now().isoformat(),
                    }
                )
            else:
                state.update(
                    {
                        "state": "running",
                        "deadline": self.deadline.isoformat() if self.deadline else None,
                        "progress": self._progress(state.get("version", "")),
                    }
                )
        elif self.process and state.get("state") == "running":
            state = self._finish(state)
        elif self.process is None and state.get("state") == "running":
            state = self._save(
                {
                    **state,
                    "state": "interrupted",
                    "message": "Training was interrupted by a monitor restart.",
                }
            )
        return state

    def start_if_scheduled(self, now: datetime | None = None) -> dict:
        now = now or datetime.now()
        if not self._in_window(now):
            return {"state": "scheduled", "message": "Waiting for the configured training window."}
        window_date = (
            now.date()
            if now.hour >= self.settings["start_hour"]
            else (now - timedelta(days=1)).date()
        )
        if self._automatic_window_date == window_date:
            return self.status()
        self._automatic_window_date = window_date
        return self.start(now)

    def start(self, now: datetime | None = None) -> dict:
        if self.process and self.process.is_alive():
            return self.status()
        summary = self.exporter.summary()
        if summary["boxes"] < self.settings["minimum_annotations"]:
            return self._save(
                {"state": "waiting", "message": "More labelled boxes are required.", **summary}
            )
        dataset = self.exporter.export()
        now = now or datetime.now()
        version = now.strftime("%Y%m%d_%H%M%S")
        stop = now.replace(hour=self.settings["stop_hour"], minute=0, second=0, microsecond=0)
        self.deadline = stop if stop > now else stop + timedelta(days=1)
        self.process = self.process_context.Process(
            target=_train,
            args=(
                str(Path(dataset["directory"]) / "dataset.yaml"),
                self.settings,
                str(self.models_directory),
                version,
            ),
            daemon=True,
        )
        self.process.start()
        return self._save(
            {
                "state": "running",
                "message": "Training started.",
                "dataset": dataset,
                "version": version,
                "started_at": now.isoformat(),
                "deadline": self.deadline.isoformat(),
            }
        )

    def model_versions(self) -> list[dict]:
        versions = []
        active_version = self.active_version()
        for manifest in sorted(self.models_directory.glob("*/model.json"), reverse=True):
            try:
                model = json.loads(manifest.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if not isinstance(model, dict):
                continue
            # Locally imported models have no Pi-side results.csv. Keep their
            # version selectable and render missing metrics as unavailable.
            model.setdefault("evaluation", {})
            model["active"] = model.get("version") == active_version
            versions.append(model)
        return versions

    def active_version(self) -> str | None:
        if not self.latest_file.exists():
            return None
        try:
            version = json.loads(self.latest_file.read_text(encoding="utf-8"))["version"]
        except (json.JSONDecodeError, KeyError, TypeError):
            return None
        return version if isinstance(version, str) and self._VERSION.fullmatch(version) else None

    def latest_model_path(self) -> Path | None:
        if not self.latest_file.exists():
            return None
        try:
            path = Path(json.loads(self.latest_file.read_text(encoding="utf-8"))["model"])
        except (json.JSONDecodeError, KeyError):
            return None
        return path if path.is_file() else None

    def activate(self, version: str) -> dict:
        if not self._VERSION.fullmatch(version):
            raise ValueError("Unknown model version.")
        manifest_file = self.models_directory / version / "model.json"
        if not manifest_file.is_file():
            raise ValueError("Unknown model version.")
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        model = Path(manifest.get("model", ""))
        if not model.is_file() or self.models_directory not in model.resolve().parents:
            raise ValueError("Model files are unavailable.")
        self.latest_file.parent.mkdir(parents=True, exist_ok=True)
        self.latest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return manifest

    def _finish(self, state: dict) -> dict:
        successful = self.process is not None and self.process.exitcode == 0
        exit_code = self.process.exitcode if self.process is not None else None
        model = self.models_directory / state["version"] / "weights" / "best.pt"
        result = {
            **state,
            "state": "completed" if successful and model.is_file() else "failed",
            "message": "Training completed."
            if successful and model.is_file()
            else self._failure_message(exit_code),
            "exit_code": exit_code,
            "finished_at": datetime.now().isoformat(),
            "model": str(model),
            "evaluation": self._evaluation(
                self.models_directory / state["version"] / "results.csv"
            ),
        }
        if result["state"] == "completed":
            manifest = {
                "version": state["version"],
                "model": str(model),
                "dataset": state.get("dataset", {}),
                "evaluation": result["evaluation"],
                "created_at": result["finished_at"],
            }
            version_directory = self.models_directory / state["version"]
            version_directory.mkdir(parents=True, exist_ok=True)
            (version_directory / "model.json").write_text(
                json.dumps(manifest, indent=2), encoding="utf-8"
            )
            self.latest_file.parent.mkdir(parents=True, exist_ok=True)
            self.latest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return self._save(result)

    @staticmethod
    def _failure_message(exit_code: int | None) -> str:
        if exit_code is None:
            return "Training worker exited before reporting a status."
        if exit_code < 0:
            try:
                reason = signal.Signals(-exit_code).name
            except ValueError:
                reason = f"signal {-exit_code}"
            return f"Training worker was terminated by {reason}."
        return f"Training worker exited with code {exit_code}."

    @staticmethod
    def _evaluation(results_file: Path) -> dict:
        if not results_file.exists():
            return {}
        with results_file.open(encoding="utf-8", newline="") as results:
            rows = list(csv.DictReader(results))
        if not rows:
            return {}
        row = rows[-1]
        wanted = {
            "metrics/precision(B)": "precision",
            "metrics/recall(B)": "recall",
            "metrics/mAP50(B)": "map50",
            "metrics/mAP50-95(B)": "map50_95",
        }
        return {name: float(row[key]) for key, name in wanted.items() if row.get(key)}

    def _progress(self, version: str) -> dict:
        results = self.models_directory / version / "results.csv"
        if not results.exists():
            return {"epochs_completed": 0, "epochs_total": self.settings["epochs"], "percent": 0}
        with results.open(encoding="utf-8", newline="") as result_file:
            completed = max(0, len(list(csv.DictReader(result_file))))
        total = self.settings["epochs"]
        return {
            "epochs_completed": completed,
            "epochs_total": total,
            "percent": round(completed / total * 100),
        }

    def _in_window(self, now: datetime) -> bool:
        start, stop = self.settings["start_hour"], self.settings["stop_hour"]
        return now.hour >= start or now.hour < stop if start > stop else start <= now.hour < stop

    def _save(self, state: dict) -> dict:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
        return state
