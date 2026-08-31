import yaml

from hornet_monitor.main import (
    merge_config,
    save_local_camera,
    save_local_roi,
    save_local_section,
    save_local_trigger_roi,
    validate_config,
)


def _config():
    return {
        "camera": {"reconnect_seconds": 5, "reconnect_max_seconds": 120},
        "night_mode": {"dark_threshold": 40, "bright_threshold": 60},
        "training": {"start_hour": 21, "stop_hour": 6, "minimum_annotations": 1, "batch": 1},
        "storage": {
            "minimum_free_gb": 1,
            "reviewed_retention_days": 30,
            "unreviewed_retention_days": 7,
            "cleanup_interval_seconds": 60,
        },
    }


def test_config_merge_validation_and_local_configuration_helpers(tmp_path):
    assert merge_config({"camera": {"width": 640}, "other": 1}, {"camera": {"fps": 30}}) == {
        "camera": {"width": 640, "fps": 30},
        "other": 1,
    }
    validate_config(_config())
    config = tmp_path / "config.yaml"
    config.write_text("{}\n", encoding="utf-8")

    save_local_roi(str(config), {"x": 1, "y": 2, "width": 3, "height": 4})
    save_local_trigger_roi(str(config), {"x": 2, "y": 3, "width": 1, "height": 1})
    save_local_camera(
        str(config), {"device": "/dev/video0", "width": 1280, "height": 720, "fps": 30}
    )
    save_local_section(str(config), "telegram", {"enabled": False})

    local = yaml.safe_load((tmp_path / "local.yaml").read_text(encoding="utf-8"))
    assert local["motion"]["roi"]["width"] == 3
    assert local["motion"]["trigger_roi"]["x"] == 2
    assert local["camera"]["device"] == "/dev/video0"
    assert local["telegram"] == {"enabled": False}


def test_camera_helper_rejects_an_unsafe_device_path(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("{}\n", encoding="utf-8")

    import pytest

    with pytest.raises(ValueError, match="Camera device"):
        save_local_camera(str(config), {"device": "/tmp/camera", "width": 1, "height": 1, "fps": 1})
