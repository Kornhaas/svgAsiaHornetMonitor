import numpy as np

from hornet_monitor.night_mode import NightMode


def test_night_mode_requires_sustained_darkness_and_resumes_with_hysteresis():
    now = [0.0]
    mode = NightMode(
        {"enabled": True, "dark_threshold": 40, "bright_threshold": 60, "dark_seconds": 20},
        clock=lambda: now[0],
    )
    dark = np.zeros((3, 3, 3), dtype=np.uint8)
    bright = np.full((3, 3, 3), 100, dtype=np.uint8)

    assert mode.observe(dark) is None
    now[0] = 20
    assert mode.observe(dark) is True
    assert mode.active
    assert mode.observe(np.full((3, 3, 3), 50, dtype=np.uint8)) is None
    assert mode.observe(bright) is False
    assert not mode.active


def test_night_mode_hides_live_preview_before_the_motion_pause():
    mode = NightMode(
        {"enabled": True, "dark_threshold": 45, "bright_threshold": 65, "dark_seconds": 1200}
    )

    mode.observe(np.zeros((2, 2, 3), dtype=np.uint8))

    assert mode.status()["preview_disabled"] is True
    assert mode.status()["pending"] is True
    assert mode.status()["active"] is False
