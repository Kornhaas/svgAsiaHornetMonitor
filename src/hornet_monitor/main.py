"""Application entry point."""

from __future__ import annotations

import argparse
import getpass
import secrets
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

import yaml
from werkzeug.security import generate_password_hash

from .activity import ActivityLog
from .background import BackgroundReference
from .camera import Camera
from .dataset import DatasetExporter
from .events import EventWriter
from .frames import crop_to_roi
from .gallery import Gallery
from .motion import MotionDetector
from .night_mode import NightMode
from .notifier import TelegramNotifier
from .predictor import Predictor
from .storage import StorageManager
from .system_status import snapshot
from .trainer import TrainingManager
from .training import TrainingStatus
from .updates import UpdateManager
from .web import create_app


def load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as config_file:
        return yaml.safe_load(config_file)


def validate_config(config: dict) -> None:
    night = config["night_mode"]
    camera = config.get("camera", {})
    storage = config["storage"]
    training = config["training"]
    if not 0 <= night["dark_threshold"] < night["bright_threshold"] <= 255:
        raise ValueError("Night-mode thresholds must be ordered between 0 and 255.")
    if training["stop_hour"] not in range(24) or training["start_hour"] not in range(24):
        raise ValueError("Training hours must be between 0 and 23.")
    if storage["minimum_free_gb"] < 0:
        raise ValueError("Minimum free storage cannot be negative.")
    if camera and (
        camera.get("reconnect_seconds", 5) < 1
        or camera.get("reconnect_max_seconds", 120) < camera.get("reconnect_seconds", 5)
    ):
        raise ValueError("Camera reconnect settings are invalid.")
    if any(
        storage.get(key, 0) < 0 for key in ("reviewed_retention_days", "unreviewed_retention_days")
    ):
        raise ValueError("Storage retention days cannot be negative.")
    if storage.get("cleanup_interval_seconds", 3600) < 60:
        raise ValueError("Storage cleanup interval must be at least 60 seconds.")
    if training["minimum_annotations"] < 1 or training.get("batch", 1) < 1:
        raise ValueError("Training minimum annotations and batch size must be positive.")


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


def save_local_trigger_roi(config_path: str, roi: dict[str, int]) -> None:
    local_path = Path(config_path).parent / "local.yaml"
    local_config = load_config(local_path) if local_path.exists() else {}
    local_config.setdefault("motion", {})["trigger_roi"] = roi
    with open(local_path, "w", encoding="utf-8") as config_file:
        yaml.safe_dump(local_config, config_file, sort_keys=False)


def save_local_camera(config_path: str, settings: dict[str, int | str | bool]) -> None:
    device = settings.get("device")
    if not isinstance(device, (int, str)) or (
        isinstance(device, str) and not device.startswith("/dev/video")
    ):
        raise ValueError("Camera device must be a numeric index or /dev/video device.")
    if any(
        not isinstance(settings.get(key), int) or settings[key] < 1
        for key in ("width", "height", "fps")
    ):
        raise ValueError("Camera width, height, and FPS must be positive integers.")
    local_path = Path(config_path).parent / "local.yaml"
    local_config = load_config(local_path) if local_path.exists() else {}
    local_config["camera"] = settings
    with open(local_path, "w", encoding="utf-8") as config_file:
        yaml.safe_dump(local_config, config_file, sort_keys=False)


def save_local_section(config_path: str, section: str, values: dict) -> None:
    local_path = Path(config_path).parent / "local.yaml"
    local_config = load_config(local_path) if local_path.exists() else {}
    local_config[section] = values
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
    validate_config(config)
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
    exporter = DatasetExporter(
        config["events"]["directory"],
        config["annotations"]["file"],
        config["training"]["datasets_directory"],
    )
    training_manager = TrainingManager(exporter, config["training"], activity_log)
    training_status = TrainingStatus(
        config["annotations"]["file"], config["training"], training_manager
    )
    event_settings = {**config["events"], "cooldown_seconds": config["motion"]["cooldown_seconds"]}
    writer = EventWriter(event_settings, activity_log)
    notifier = TelegramNotifier(config["telegram"], activity_log)
    predictor = Predictor(
        config["training"]["models_directory"],
        config["annotations"]["predictions_file"],
        notifier,
        activity_log,
    )
    detector = MotionDetector(config["motion"])
    night_mode = NightMode(config["night_mode"])

    def event_frame(frame=None):
        frame = camera.get_frame() if frame is None else frame
        if frame is None:
            return None
        return (
            crop_to_roi(frame, detector.roi())
            if config["events"].get("crop_to_roi", True)
            else frame
        )

    background = BackgroundReference(
        config["background"]["image_file"],
        config["background"]["metadata_file"],
        config["background"]["proposal_minimum_area"],
    )
    storage = StorageManager(
        config["storage"],
        [
            config["events"]["directory"],
            config["annotations"]["file"],
            config["background"]["image_file"],
            config["training"]["models_directory"],
        ],
        config["events"]["directory"],
        config["annotations"]["file"],
    )

    writer.frame_supplier = event_frame
    state = {"motion": False, "largest_area": 0.0, "last_event": None}
    state_lock = threading.Lock()
    last_camera_error = None
    last_cleanup = 0.0
    storage_alerted = False
    last_training_minute = None
    last_training_state = None

    def monitor() -> None:
        nonlocal \
            last_camera_error, \
            last_cleanup, \
            storage_alerted, \
            last_training_minute, \
            last_training_state
        while True:
            predictor.reap()
            if camera.error != last_camera_error:
                last_camera_error = camera.error
                if camera.error:
                    activity_log.record(
                        "camera_offline", "Camera offline; reconnecting", level="error"
                    )
                    notifier.alert(
                        "camera_offline", "Camera is offline; reconnect attempts are active."
                    )
                else:
                    activity_log.record("camera_online", "Camera stream restored")
            now_monotonic = time.monotonic()
            if now_monotonic - last_cleanup >= config["storage"]["cleanup_interval_seconds"]:
                result = storage.cleanup()
                last_cleanup = now_monotonic
                if result["deleted"]:
                    activity_log.record(
                        "storage_cleanup", "Old event images removed", details=result
                    )
                warning = storage.status()["warning"]
                if warning and not storage_alerted:
                    storage_alerted = True
                    activity_log.record("storage_low", "Low free storage", level="error")
                    notifier.alert("low_storage", "Free storage is below the configured limit.")
                elif not warning:
                    storage_alerted = False
            frame = camera.get_frame()
            if frame is None:
                time.sleep(0.1)
                continue
            transition = night_mode.observe(event_frame(frame))
            if transition is True:
                activity_log.record(
                    "night_mode_started",
                    "Night mode started; motion capture paused and training window is available.",
                    details=night_mode.status(),
                )
            elif transition is False:
                detector.reset()
                activity_log.record(
                    "night_mode_ended",
                    "Daylight returned; motion capture resumed.",
                    details=night_mode.status(),
                )
            minute = datetime.now().strftime("%Y%m%d%H%M")
            if minute != last_training_minute:
                last_training_minute = minute
                training_state = training_manager.status()
                if night_mode.active and training_state["state"] != "running":
                    training_state = training_manager.start_if_scheduled()
                if (
                    training_state["state"] == "failed"
                    and training_state["state"] != last_training_state
                ):
                    activity_log.record("training_failed", "Training failed", level="error")
                    notifier.alert("training_failed", "The overnight training job failed.")
                last_training_state = training_state["state"]
            if night_mode.active:
                with state_lock:
                    state.update(motion=False, largest_area=0.0)
                time.sleep(0.2)
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
                saved_image = Path(writer.last_event) / "frame_000.jpg"
                image_id = saved_image.relative_to(Path(config["events"]["directory"])).as_posix()
                predictor.submit(str(saved_image), image_id)
            time.sleep(0.05)

    threading.Thread(target=monitor, name="motion-monitor", daemon=True).start()

    def status():
        with state_lock:
            return {
                **state,
                "camera_error": camera.error,
                "roi": detector.roi(),
                "trigger_roi": detector.trigger_roi(),
                "frame_width": config["camera"]["width"],
                "frame_height": config["camera"]["height"],
                "event_crop": config["events"].get("crop_to_roi", True),
                "night_mode": night_mode.status(),
            }

    def update_roi(roi: dict[str, int]) -> dict[str, int]:
        if "trigger" in roi:
            updated_trigger = detector.update_trigger_roi(
                roi["trigger"], config["camera"]["width"], config["camera"]["height"]
            )
            save_local_trigger_roi(args.config, updated_trigger)
            activity_log.record(
                "trigger_roi_updated", "Trigger region updated", details=updated_trigger
            )
            return updated_trigger
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
            details={"image": saved["image"], "count": len(saved.get("annotations", [saved]))},
        )
        return saved

    def delete_event(event_id: str) -> None:
        gallery.delete_event(event_id)
        activity_log.record(
            "event_deleted", "Event deleted from gallery", details={"event": event_id}
        )

    def update_camera(settings: dict) -> None:
        save_local_camera(args.config, settings)
        activity_log.record(
            "camera_updated", "Camera settings saved; restarting monitor", details=settings
        )
        subprocess.Popen(["sudo", "-n", "systemctl", "restart", config["updates"]["service"]])

    def update_telegram(settings: dict) -> None:
        required = {"enabled", "bot_token", "chat_id", "confidence_threshold", "cooldown_seconds"}
        if set(settings) != required or not isinstance(settings["enabled"], bool):
            raise ValueError("Invalid Telegram settings.")
        settings["confidence_threshold"] = float(settings["confidence_threshold"])
        settings["cooldown_seconds"] = int(settings["cooldown_seconds"])
        if not 0 < settings["confidence_threshold"] <= 1 or settings["cooldown_seconds"] < 1:
            raise ValueError("Invalid Telegram threshold or cooldown.")
        save_local_section(args.config, "telegram", settings)
        activity_log.record("telegram_updated", "Telegram settings saved; restarting monitor")
        subprocess.Popen(["sudo", "-n", "systemctl", "restart", config["updates"]["service"]])

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
        background,
        event_frame,
        lambda: {
            **snapshot(config["events"]["directory"]),
            "night_mode": night_mode.status(),
            "storage": storage.status(),
        },
        training_manager,
        update_camera,
        update_telegram,
        storage,
        predictor.history,
    )
    app.run(
        host=config["web"]["host"],
        port=config["web"]["port"],
        debug=config["web"].get("debug", False),
        threaded=True,
    )


if __name__ == "__main__":
    main()
