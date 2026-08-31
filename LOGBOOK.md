# Project logbook

This log records implementation milestones and decisions. Add a dated entry whenever behavior, deployment, or architecture changes in a way that matters to future work.

## 2026-08-31 — V0.1 foundation

Created the initial Raspberry Pi camera-monitoring application.

- Added a modular Python package for camera capture, ROI motion detection, event writing, and the Flask web interface.
- Configured `/dev/video0` for 1280 × 720 MJPEG at 30 FPS in `config/config.yaml`.
- Added an MJPEG live stream and browser status display at port 8000.
- Added ROI-only, lightweight background-subtraction motion detection.
- Added date/time-organized event folders and configurable JPEG bursts in `data/events/`.
- Excluded events, captures, logs, local configuration, and virtual environments from Git.
- Added motion-detector unit tests and verified the web UI with a smoke test.

## 2026-08-31 — Dependency workflow

Moved dependency management from `requirements.txt` to uv.

- Added `pyproject.toml` and checked-in `uv.lock`.
- Added the `hornet-monitor` command, run through `uv run hornet-monitor`.
- Updated the Raspberry Pi setup and test instructions to use `uv sync --locked` and `uv run`.
- Verified installation, tests, and web-UI smoke test using the locked environment.

## Next planned milestone

Test the webcam and ROI settings on the Raspberry Pi, then tune `min_area`, threshold, cooldown, and burst settings using real captures. Keep image collection stable before introducing any classification model.
