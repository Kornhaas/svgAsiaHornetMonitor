import json
from datetime import datetime

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
