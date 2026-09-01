import json
from datetime import datetime
from pathlib import Path

import ultralytics

import hornet_monitor.predictor as predictor_module
import hornet_monitor.trainer as trainer_module
from hornet_monitor.dataset import DatasetExporter
from hornet_monitor.notifier import TelegramNotifier
from hornet_monitor.predictor import Predictor
from hornet_monitor.trainer import TrainingManager


def test_telegram_is_inert_when_disabled():
    notifier = TelegramNotifier(
        {"enabled": False, "confidence_threshold": 0.8, "cooldown_seconds": 1}
    )

    assert not notifier.notify({"label": "bee", "confidence": 0.1, "image": "event.jpg"})


def test_telegram_builds_photo_request_when_event_image_exists(tmp_path):
    image = tmp_path / "event.jpg"
    image.write_bytes(b"jpg")

    request = TelegramNotifier._request("token", "chat", "message", str(image))

    assert request.full_url.endswith("/sendPhoto")
    assert b"jpg" in request.data


def test_telegram_builds_message_request_for_operational_alert():
    notifier = TelegramNotifier(
        {"enabled": True, "bot_token": "token", "chat_id": "chat", "cooldown_seconds": 1}
    )

    request = notifier._request("token", "chat", "Camera offline", "")

    assert request.full_url.endswith("/sendMessage")
    assert b"Camera+offline" in request.data


def test_predictor_does_nothing_without_a_trained_model(tmp_path):
    predictor = Predictor(str(tmp_path / "models"), str(tmp_path / "predictions.jsonl"))

    predictor._predict("event.jpg")

    assert not (tmp_path / "predictions.jsonl").exists()


def test_predictor_returns_newest_prediction_history_first(tmp_path):
    predictions = tmp_path / "predictions.jsonl"
    predictions.write_text('{"label":"bee"}\n{"label":"wasp"}\n', encoding="utf-8")
    predictor = Predictor(str(tmp_path / "models"), str(predictions))

    assert [item["label"] for item in predictor.history()] == ["wasp", "bee"]


def test_predictor_limits_native_inference_to_one_isolated_process(tmp_path, monkeypatch):
    model = tmp_path / "models" / "version" / "weights" / "best.pt"
    model.parent.mkdir(parents=True)
    model.write_bytes(b"model")
    (model.parents[2] / "latest.json").write_text(
        json.dumps({"model": str(model)}), encoding="utf-8"
    )
    records = []

    class Activity:
        path = tmp_path / "activity.jsonl"

        def record(self, *args, **kwargs):
            records.append((args, kwargs))

    class Process:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.alive, self.exitcode = True, None

        def start(self):
            return None

        def is_alive(self):
            return self.alive

        def join(self):
            return None

        def close(self):
            return None

    processes = []

    class Context:
        def Process(self, **kwargs):
            process = Process(**kwargs)
            processes.append(process)
            return process

    monkeypatch.setattr(predictor_module.multiprocessing, "get_context", lambda _name: Context())
    predictor = Predictor(
        str(model.parents[2]), str(tmp_path / "predictions.jsonl"), activity_log=Activity()
    )

    assert predictor.submit("event.jpg", "2026-09-01/123000_000001/frame_000.jpg")
    assert not predictor.submit("second-event.jpg")
    assert len(processes) == 1
    assert processes[0].kwargs["args"][3] == "2026-09-01/123000_000001/frame_000.jpg"
    assert records[-1][0][0] == "prediction_skipped"
    processes[0].alive, processes[0].exitcode = False, -4

    predictor.reap()

    assert records[-1][0][0] == "prediction_failed"
    assert records[-1][1]["details"] == {"exit_code": -4}


def test_predictor_limits_worker_cpu_use_on_the_pi():
    source = (Path(__file__).parents[1] / "src" / "hornet_monitor" / "predictor.py").read_text(
        encoding="utf-8"
    )

    assert 'os.environ.setdefault("OMP_NUM_THREADS", "1")' in source
    assert "torch.set_num_threads(1)" in source
    assert "torch.set_num_interop_threads(1)" in source


def test_training_manager_waits_for_enough_labelled_boxes(tmp_path):
    exporter = DatasetExporter(
        str(tmp_path / "events"),
        str(tmp_path / "annotations.jsonl"),
        str(tmp_path / "datasets"),
    )
    manager = TrainingManager(
        exporter,
        {"models_directory": str(tmp_path / "models"), "minimum_annotations": 1, "stop_hour": 6},
    )

    state = manager.start()

    assert state["state"] == "waiting"
    assert manager.status()["state"] == "waiting"


def test_training_manager_reports_a_native_worker_signal(tmp_path):
    exporter = DatasetExporter(
        str(tmp_path / "events"),
        str(tmp_path / "annotations.jsonl"),
        str(tmp_path / "datasets"),
    )
    manager = TrainingManager(
        exporter,
        {"models_directory": str(tmp_path / "models"), "minimum_annotations": 1, "stop_hour": 6},
    )
    manager.process = type(
        "FinishedProcess", (), {"exitcode": -4, "is_alive": lambda self: False}
    )()
    manager._save({"state": "running", "version": "20260901_210300"})

    state = manager.status()

    assert state["state"] == "failed"
    assert state["exit_code"] == -4
    assert state["message"] == "Training worker was terminated by SIGILL."


def test_pi_training_disables_the_unsafe_automatic_amp_check(monkeypatch):
    options = {}
    enabled = []

    class Model:
        def train(self, **kwargs):
            options.update(kwargs)

    monkeypatch.setattr(ultralytics, "YOLO", lambda _: Model())
    monkeypatch.setattr(
        trainer_module.faulthandler, "enable", lambda **kwargs: enabled.append(kwargs)
    )

    trainer_module._train(
        "dataset.yaml",
        {"model_name": "yolo11n.pt", "epochs": 30, "image_size": 320},
        "models",
        "v1",
    )

    assert options["device"] == "cpu"
    assert options["amp"] is False
    assert options["trainer"].__name__ == "PiDetectionTrainer"
    assert enabled == [{"all_threads": True}]


def test_training_manager_only_schedules_inside_the_overnight_window(tmp_path):
    exporter = DatasetExporter(
        str(tmp_path / "events"), str(tmp_path / "annotations.jsonl"), str(tmp_path / "datasets")
    )
    manager = TrainingManager(
        exporter,
        {
            "models_directory": str(tmp_path / "models"),
            "minimum_annotations": 1,
            "stop_hour": 6,
            "start_hour": 21,
        },
    )

    state = manager.start_if_scheduled(datetime(2026, 9, 1, 20, 30))

    assert state["state"] == "scheduled"


def test_training_manager_activates_a_versioned_model_and_reports_progress(tmp_path):
    models = tmp_path / "models"
    version = "20260901_210000"
    model = models / version / "weights" / "best.pt"
    model.parent.mkdir(parents=True)
    model.write_bytes(b"model")
    (models / version / "model.json").write_text(
        json.dumps({"version": version, "model": str(model)}), encoding="utf-8"
    )
    (models / version / "results.csv").write_text("epoch\n0\n1\n", encoding="utf-8")
    exporter = DatasetExporter(
        str(tmp_path / "events"), str(tmp_path / "annotations.jsonl"), str(tmp_path / "datasets")
    )
    manager = TrainingManager(
        exporter,
        {
            "models_directory": str(models),
            "minimum_annotations": 1,
            "stop_hour": 6,
            "start_hour": 21,
            "epochs": 4,
        },
    )

    activated = manager.activate(version)

    assert activated["version"] == version
    assert manager.active_version() == version
    assert manager.latest_model_path() == model
    assert manager.model_versions() == [
        {"version": version, "model": str(model), "evaluation": {}, "active": True}
    ]
    assert manager._progress(version) == {"epochs_completed": 2, "epochs_total": 4, "percent": 50}
