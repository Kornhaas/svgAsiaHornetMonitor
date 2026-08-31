import pytest

from hornet_monitor.main import validate_config


def test_config_rejects_reversed_night_thresholds():
    config = {
        "night_mode": {"dark_threshold": 70, "bright_threshold": 50},
        "training": {"start_hour": 21, "stop_hour": 6},
        "storage": {"minimum_free_gb": 1},
    }

    with pytest.raises(ValueError, match="thresholds"):
        validate_config(config)
