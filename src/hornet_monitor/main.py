"""Application entry point."""

from __future__ import annotations

import argparse
import getpass
import secrets
import threading
import time
from pathlib import Path

import yaml
from werkzeug.security import generate_password_hash

from .activity import ActivityLog
from .camera import Camera
from .events import EventWriter
from .frames import crop_to_roi
from .gallery import Gallery
from .motion import MotionDetector
from .training import TrainingStatus
from .updates import UpdateManager
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


def configure_auth(config_path: str, username: str) -> None:
    password = getpass.getpass("Password for the web interface: ")
    if not password:
        raise ValueError("Password must not be empty.")
    local_path = Path(config_path).parent / "local.yaml"
    local_config = load_config(local_path) if local_path.exists() else {}
    local_config.setdefault("web", {})["auth"] = {
        "enabled": True,
        "username": username,
        "password_hash": generate_password_hash(password),
        "secret_key": secrets.token_urlsafe(32),
    }
    local_config.setdefault("updates", {})["enabled"] = True
    local_config["updates"]["uv_binary"] = str(Path.home() / ".local/bin/uv")
    with open(local_path, "w", encoding="utf-8") as config_file:
        yaml.safe_dump(local_config, config_file, sort_keys=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Asia Hornet Monitor")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--setup-auth", action="store_true")
    parser.add_argument("--username", default="hornet")
    args = parser.parse_args()
    config = load_config(args.config)
    local_path = Path(args.config).parent / "local.yaml"
    if local_path.exists() and Path(args.config) != local_path:
        config = merge_config(config, load_config(local_path))
    if args.setup_auth:
        configure_auth(args.config, args.username)
        print("Web access protection configured.")
        return
    camera = Camera(config["camera"])
    camera.start()
    activity_log = ActivityLog(config["activity"]["file"])
    activity_log.record("monitor_started", "Asia Hornet Monitor started")
    update_manager = UpdateManager(config["updates"], activity_log)
    gallery = Gallery(config["events"]["directory"], config["annotations"]["file"])
    training_status = TrainingStatus(config["annotations"]["file"], config["training"])
    event_settings = {**config["events"], "cooldown_seconds": config["motion"]["cooldown_seconds"]}
    writer = EventWriter(event_settings, activity_log)
    detector = MotionDetector(config["motion"])

    def event_frame(frame=None):
        frame = camera.get_frame() if frame is None else frame
        if frame is None:
            return None
        return (
            crop_to_roi(frame, detector.roi())
            if config["events"].get("crop_to_roi", True)
            else frame
        )

    writer.frame_supplier = event_frame
    state = {"motion": False, "largest_area": 0.0, "last_event": None}
    state_lock = threading.Lock()

    def monitor() -> None:
        while True:
            frame = camera.get_frame()
            if frame is None:
                time.sleep(0.1)
                continue
            result = detector.detect(frame)
            saved = result.detected and writer.save_burst(event_frame(frame))
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
                "event_crop": config["events"].get("crop_to_roi", True),
            }

    def update_roi(roi: dict[str, int]) -> dict[str, int]:
        updated_roi = detector.update_roi(
            roi, config["camera"]["width"], config["camera"]["height"]
        )
        save_local_roi(args.config, updated_roi)
        activity_log.record("roi_updated", "Region of interest updated", details=updated_roi)
        return updated_roi

    def save_annotation(annotation: dict) -> dict:
        saved = gallery.annotate(annotation)
        activity_log.record(
            "annotation_saved",
            "Image annotation saved",
            details={"label": saved["label"], "image": saved["image"]},
        )
        return saved

    def delete_event(event_id: str) -> None:
        gallery.delete_event(event_id)
        activity_log.record(
            "event_deleted", "Event deleted from gallery", details={"event": event_id}
        )

    app = create_app(
        camera,
        status,
        update_roi,
        activity_log,
        config["web"]["auth"],
        update_manager,
        gallery,
        save_annotation,
        delete_event,
        training_status,
    )
    app.run(
        host=config["web"]["host"],
        port=config["web"]["port"],
        debug=config["web"].get("debug", False),
        threaded=True,
    )


if __name__ == "__main__":
    main()
