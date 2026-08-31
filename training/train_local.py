"""Train a local YOLO model from one versioned dataset export."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def find_dataset(directory: Path) -> Path:
    datasets = sorted(directory.glob("*/dataset.yaml"), reverse=True)
    if not datasets:
        raise FileNotFoundError(f"No dataset.yaml found below {directory}.")
    return datasets[0]


def resolve_device(value: str) -> str | int:
    if value != "auto":
        return value
    try:
        import torch

        return 0 if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


def parse_arguments() -> argparse.Namespace:
    root = repository_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        help="Path to a dataset.yaml; defaults to the most recent local export.",
    )
    parser.add_argument("--datasets", type=Path, default=root / "data/datasets")
    parser.add_argument("--output", type=Path, default=root / "data/models/local-experiments")
    parser.add_argument("--model", default="yolo11n.pt", help="YOLO base model or local .pt path.")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--image-size", type=int, default=640)
    parser.add_argument("--batch", type=int, default=-1, help="-1 lets YOLO choose automatically.")
    parser.add_argument(
        "--device", default="auto", help="auto, cpu, 0, or another Ultralytics device."
    )
    parser.add_argument(
        "--workers", type=int, default=0, help="Use 0 for reliable Windows operation."
    )
    parser.add_argument("--name", help="Run name; default is a timestamp.")
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    dataset = args.dataset or find_dataset(args.datasets)
    if not dataset.is_file():
        raise SystemExit(f"Dataset configuration not found: {dataset}")
    if args.epochs < 1 or args.image_size < 32 or args.workers < 0:
        raise SystemExit(
            "Epochs must be positive, image size at least 32, and workers non-negative."
        )

    from ultralytics import YOLO

    name = args.name or datetime.now().strftime("local_%Y%m%d_%H%M%S")
    output = args.output.resolve()
    device = resolve_device(args.device)
    print(f"Training dataset: {dataset.resolve()}")
    print(f"Device: {device}; output: {output / name}")
    YOLO(args.model).train(
        data=str(dataset.resolve()),
        epochs=args.epochs,
        imgsz=args.image_size,
        batch=args.batch,
        device=device,
        workers=args.workers,
        project=str(output),
        name=name,
        exist_ok=False,
    )
    print(f"\nTraining completed. Model: {output / name / 'weights/best.pt'}")


if __name__ == "__main__":
    main()
