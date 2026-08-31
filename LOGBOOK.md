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

## 2026-08-31 — Project engineering baseline

Added an AI-assisted engineering workflow and automated quality foundation.

- Added architecture documentation with runtime flow, component ownership, configuration rules, and a future classifier boundary.
- Added an AI collaboration guide with architect/developer/test/review roles, change protocol, reusable task prompt, and Pi hardware checklist.
- Added pytest and Ruff as development dependencies managed by uv.
- Added a GitHub Actions workflow to install the lockfile, check formatting, lint, and run tests on pushes and pull requests.
- Added a web route test and standardized local verification around pytest and Ruff.
