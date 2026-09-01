import json

import cv2
import numpy as np

from hornet_monitor.dataset import DatasetExporter


def test_dataset_export_writes_yolo_labels_and_ignores_empty_entries(tmp_path):
    events = tmp_path / "events"
    image = events / "2026-01-01" / "event" / "frame_000.jpg"
    image.parent.mkdir(parents=True)
    cv2.imwrite(str(image), np.zeros((100, 200, 3), dtype=np.uint8))
    annotations = tmp_path / "annotations.jsonl"
    annotations.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "image": "2026-01-01/event/frame_000.jpg",
                        "label": "bee",
                        "box": {"x": 20, "y": 10, "width": 40, "height": 20},
                    }
                ),
                json.dumps(
                    {"image": "2026-01-01/event/frame_000.jpg", "label": "empty", "box": None}
                ),
            ]
        ),
        encoding="utf-8",
    )
    exported = DatasetExporter(str(events), str(annotations), str(tmp_path / "datasets")).export()

    assert exported["boxes"] == 1
    assert sum(exported["export_splits"].values()) == 1
    labels = list((tmp_path / "datasets" / exported["version"] / "labels").rglob("*.txt"))
    assert labels[0].read_text().startswith("3 0.200000 0.200000 0.200000 0.200000")
    assert "goldfly" in (tmp_path / "datasets" / exported["version"] / "dataset.yaml").read_text()
    assert "fleshfly" in (tmp_path / "datasets" / exported["version"] / "dataset.yaml").read_text()


def test_dataset_export_creates_manifest_when_annotated_images_are_missing(tmp_path):
    annotations = tmp_path / "annotations.jsonl"
    annotations.write_text(
        json.dumps(
            {
                "image": "2026-01-01/missing/frame_000.jpg",
                "label": "empty",
                "box": None,
            }
        ),
        encoding="utf-8",
    )

    exported = DatasetExporter(
        str(tmp_path / "events"), str(annotations), str(tmp_path / "datasets")
    ).export()

    destination = tmp_path / "datasets" / exported["version"]
    assert exported["skipped_images"] == 1
    assert (destination / "dataset.yaml").exists()
    assert (destination / "manifest.json").exists()
