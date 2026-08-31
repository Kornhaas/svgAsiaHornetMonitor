import json

from hornet_monitor.training import TrainingStatus


def test_training_overview_counts_annotations_and_reports_readiness(tmp_path):
    annotations = tmp_path / "annotations.jsonl"
    annotations.write_text(
        "\n".join(
            [
                json.dumps({"image": "2026-08-31/a/frame_000.jpg", "label": "bee"}),
                json.dumps({"image": "2026-08-31/b/frame_000.jpg", "label": "empty"}),
                json.dumps({"image": "2026-08-31/a/frame_000.jpg", "label": "bee"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    overview = TrainingStatus(
        annotations, {"minimum_annotations": 3, "start_hour": 21, "stop_hour": 6}
    ).overview()

    assert overview["reviewed_images"] == 2
    assert overview["annotations"] == 3
    assert overview["labels"] == {"bee": 2, "empty": 1}
    assert overview["ready"] is True
    assert overview["schedule"] == {"start_hour": 21, "stop_hour": 6}
