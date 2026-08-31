from hornet_monitor.dataset import DatasetExporter
from hornet_monitor.notifier import TelegramNotifier
from hornet_monitor.predictor import Predictor
from hornet_monitor.trainer import TrainingManager


def test_telegram_is_inert_when_disabled():
    notifier = TelegramNotifier(
        {"enabled": False, "confidence_threshold": 0.8, "cooldown_seconds": 1}
    )

    assert not notifier.notify({"label": "bee", "confidence": 0.1, "image": "event.jpg"})


def test_predictor_does_nothing_without_a_trained_model(tmp_path):
    predictor = Predictor(str(tmp_path / "models"), str(tmp_path / "predictions.jsonl"))

    predictor._predict("event.jpg")

    assert not (tmp_path / "predictions.jsonl").exists()


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
