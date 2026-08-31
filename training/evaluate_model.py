"""Evaluate a trained local YOLO model against a versioned validation dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from train_local import find_dataset, repository_root, resolve_device


def parse_arguments() -> argparse.Namespace:
    root = repository_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path, help="Path to a trained best.pt model.")
    parser.add_argument("--dataset", type=Path, help="Path to a dataset.yaml.")
    parser.add_argument("--datasets", type=Path, default=root / "data/datasets")
    parser.add_argument("--split", choices=("val", "test"), default="val")
    parser.add_argument("--device", default="auto")
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    dataset = args.dataset or find_dataset(args.datasets)
    if not args.model.is_file() or not dataset.is_file():
        raise SystemExit("Model and dataset configuration must both exist.")

    from ultralytics import YOLO

    metrics = YOLO(str(args.model)).val(
        data=str(dataset.resolve()), split=args.split, device=resolve_device(args.device), workers=0
    )
    print(json.dumps(getattr(metrics, "results_dict", {}), indent=2, default=str))


if __name__ == "__main__":
    main()
