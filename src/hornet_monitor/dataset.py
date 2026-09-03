"""Deterministic local YOLO dataset export from reviewed gallery annotations."""

from __future__ import annotations

import hashlib
import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import cv2
import yaml

CLASSES = [
    "vespa_velutina",
    "vespa_crabro",
    "wasp",
    "bee",
    "other",
    "goldfly",
    "fleshfly",
    "blue_blowfly",
    # Append new classes so existing YOLO class IDs remain stable.
    "ant",
]


class DatasetExporter:
    def __init__(self, events_directory: str, annotations_file: str, output_directory: str) -> None:
        self.events_directory = Path(events_directory)
        self.annotations_file = Path(annotations_file)
        self.output_directory = Path(output_directory)

    def summary(self) -> dict:
        annotations = self._annotations()
        counts = Counter(entry["label"] for entry in annotations if entry.get("label") in CLASSES)
        images = {entry["image"] for entry in annotations if entry.get("label") in CLASSES}
        splits = Counter(self._split(image) for image in images)
        return {
            "images": len(images),
            "boxes": sum(counts.values()),
            "labels": dict(counts),
            "splits": {split: splits[split] for split in ("train", "val", "test")},
        }

    def export(self) -> dict:
        version = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        destination = self.output_directory / version
        destination.mkdir(parents=True, exist_ok=False)
        grouped: dict[str, list[dict]] = defaultdict(list)
        for entry in self._annotations():
            if (entry.get("label") in CLASSES and entry.get("box")) or entry.get(
                "label"
            ) == "empty":
                grouped[entry["image"]].append(entry)
        split_images = Counter()
        empty_images = 0
        skipped_images = 0
        for image_id, entries in grouped.items():
            source = self.events_directory / image_id
            if not source.is_file():
                skipped_images += 1
                continue
            image = cv2.imread(str(source))
            if image is None:
                skipped_images += 1
                continue
            split = self._split(image_id)
            split_images[split] += 1
            stem = hashlib.sha256(image_id.encode()).hexdigest()[:16]
            image_target = destination / "images" / split / f"{stem}.jpg"
            label_target = destination / "labels" / split / f"{stem}.txt"
            image_target.parent.mkdir(parents=True, exist_ok=True)
            label_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, image_target)
            height, width = image.shape[:2]
            boxes = [
                entry for entry in entries if entry.get("label") in CLASSES and entry.get("box")
            ]
            if boxes:
                label_target.write_text(
                    "\n".join(self._yolo_line(entry, width, height) for entry in boxes) + "\n"
                )
            else:
                empty_images += 1
        metadata = {
            "path": str(destination.resolve()),
            "train": "images/train",
            "val": "images/val",
            "test": "images/test",
            "names": CLASSES,
        }
        (destination / "dataset.yaml").write_text(
            yaml.safe_dump(metadata, sort_keys=False), encoding="utf-8"
        )
        result = {
            "version": version,
            "directory": str(destination),
            **self.summary(),
            "export_splits": {split: split_images[split] for split in ("train", "val", "test")},
            "empty_images": empty_images,
            "skipped_images": skipped_images,
        }
        (destination / "manifest.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result

    def _annotations(self) -> list[dict]:
        if not self.annotations_file.exists():
            return []
        return [
            json.loads(line)
            for line in self.annotations_file.read_text(encoding="utf-8").splitlines()
            if line
        ]

    @staticmethod
    def _split(image_id: str) -> str:
        event_id = image_id.rsplit("/", maxsplit=1)[0]
        value = int(hashlib.sha256(event_id.encode()).hexdigest(), 16) % 100
        return "train" if value < 70 else "val" if value < 90 else "test"

    @staticmethod
    def _yolo_line(entry: dict, image_width: int, image_height: int) -> str:
        box = entry["box"]
        center_x = (box["x"] + box["width"] / 2) / image_width
        center_y = (box["y"] + box["height"] / 2) / image_height
        box_width = box["width"] / image_width
        box_height = box["height"] / image_height
        values = (CLASSES.index(entry["label"]), center_x, center_y, box_width, box_height)
        return "{} {:.6f} {:.6f} {:.6f} {:.6f}".format(*values)
