import json

from hornet_monitor.active_learning import ActiveLearningStatus


def test_active_learning_reports_auditable_feedback_calibration_and_gates(tmp_path):
    annotations = tmp_path / "annotations.jsonl"
    predictions = tmp_path / "predictions.jsonl"
    predictions.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "id": "accepted",
                        "image": "event/a.jpg",
                        "label": "fleshfly",
                        "confidence": 0.99,
                        "model_version": "model-a",
                        "best_in_burst": True,
                        "brightness": 50,
                    }
                ),
                json.dumps(
                    {
                        "id": "empty",
                        "image": "event/b.jpg",
                        "label": "fleshfly",
                        "confidence": 0.99,
                        "model_version": "model-a",
                        "best_in_burst": True,
                        "brightness": 90,
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    annotations.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "image": "event/a.jpg",
                        "label": "fleshfly",
                        "source": "model_confirmed",
                        "prediction_id": "accepted",
                    }
                ),
                json.dumps({"image": "event/b.jpg", "label": "empty", "source": "manual"}),
            ]
        ),
        encoding="utf-8",
    )
    settings = {
        "auto_accept_enabled": False,
        "auto_accept_confidence": 0.98,
        "auto_accept_min_samples": 1,
        "auto_accept_min_precision": 0.9,
        "auto_accept_labels": ["fleshfly"],
        "target_per_class": 3,
    }
    service = ActiveLearningStatus(
        annotations,
        predictions,
        settings,
    )
    status = service.overview()

    assert status["feedback"] == {"accepted": 1, "empty": 1}
    assert status["calibration"]["fleshfly"] == {"samples": 2, "precision": 0.5}
    assert status["auto_accept"]["gates"]["fleshfly"]["permitted"] is False
    assert status["brightness"] == {"samples": 2, "mean": 70.0, "range": 40.0}
    assert service.automatic_candidates() == []
