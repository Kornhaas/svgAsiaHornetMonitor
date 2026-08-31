"""Application entry point."""

from __future__ import annotations

import argparse
import threading
import time
from pathlib import Path

import yaml

from .camera import Camera
from .events import EventWriter
from .motion import MotionDetector
from .web import create_app


def load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as config_file:
        return yaml.safe_load(config_file)


def merge_config(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        merged[key] = (
            merge_config(merged[key], value)
            if isinstance(value, dict) and isinstance(merged.get(key), dict)
            else value
        )
    return merged


def save_local_roi(config_path: str, roi: dict[str, int]) -> None:
    local_path = Path(config_path).parent / "local.yaml"
    local_config = load_config(local_path) if local_path.exists() else {}
    local_config.setdefault("motion", {})["roi"] = roi
    with open(local_path, "w", encoding="utf-8") as config_file:
        yaml.safe_dump(local_config, config_file, sort_keys=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Asia Hornet Monitor")
    parser.add_argument("--config", default="config/config.yaml")
    args = parser.parse_args()
    config = load_config(args.config)
    local_path = Path(args.config).parent / "local.yaml"
    if local_path.exists() and Path(args.config) != local_path:
        config = merge_config(config, load_config(local_path))
    camera = Camera(config["camera"])
    camera.start()
    event_settings = {**config["events"], "cooldown_seconds": config["motion"]["cooldown_seconds"]}
    writer = EventWriter(event_settings)
    writer.frame_supplier = camera.get_frame
    detector = MotionDetector(config["motion"])
    state = {"motion": False, "largest_area": 0.0, "last_event": None}
    state_lock = threading.Lock()

    def monitor() -> None:
        while True:
            frame = camera.get_frame()
            if frame is None:
                time.sleep(0.1)
                continue
            result = detector.detect(frame)
            saved = result.detected and writer.save_burst(frame)
            with state_lock:
                state.update(
                    motion=result.detected,
                    largest_area=round(result.largest_area, 1),
                    last_event=writer.last_event,
                )
            if saved:
                print(f"Motion event saved to {writer.last_event}")
            time.sleep(0.05)

    threading.Thread(target=monitor, name="motion-monitor", daemon=True).start()

    def status():
        with state_lock:
            return {
                **state,
                "camera_error": camera.error,
                "roi": detector.roi(),
                "frame_width": config["camera"]["width"],
                "frame_height": config["camera"]["height"],
            }

    def update_roi(roi: dict[str, int]) -> dict[str, int]:
        updated_roi = detector.update_roi(
            roi, config["camera"]["width"], config["camera"]["height"]
        )
        save_local_roi(args.config, updated_roi)
        return updated_roi

    app = create_app(camera, status, update_roi)
    app.run(
        host=config["web"]["host"],
        port=config["web"]["port"],
        debug=config["web"].get("debug", False),
        threaded=True,
    )


if __name__ == "__main__":
    main()
