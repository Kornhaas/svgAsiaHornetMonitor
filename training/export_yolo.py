"""Create a versioned YOLO export from confirmed local gallery annotations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from hornet_monitor.dataset import DatasetExporter


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_arguments() -> argparse.Namespace:
    root = repository_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--events", type=Path, default=root / "data/events", help="Event image directory."
    )
    parser.add_argument(
        "--annotations",
        type=Path,
        default=root / "data/annotations.jsonl",
        help="Gallery annotation JSONL file.",
    )
    parser.add_argument(
        "--output", type=Path, default=root / "data/datasets", help="Dataset export directory."
    )
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    result = DatasetExporter(str(args.events), str(args.annotations), str(args.output)).export()
    print(json.dumps(result, indent=2))
    print(f"\nDataset configuration: {Path(result['directory']) / 'dataset.yaml'}")


if __name__ == "__main__":
    main()
