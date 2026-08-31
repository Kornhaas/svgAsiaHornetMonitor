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

## 2026-08-31 — Raspberry Pi OS Trixie setup correction

- Removed `libatlas-base-dev` from the installation command because Trixie does not provide that package and this project does not require it.
- Added the immediate `PATH` export required after uv's user-local installation, before the shell is restarted.
- Limited the production Pi installation to runtime dependencies with `uv sync --locked --no-dev`.

## 2026-08-31 — Browser icon

- Added a lightweight, local SVG hornet favicon and linked it from the web interface.

## 2026-08-31 — Interactive region of interest

- Added an ROI rectangle on the live image, adjustable by dragging or through numeric fields.
- Added validated runtime ROI updates through the web API; each update resets the motion background model.
- Persisted the per-device ROI in ignored `config/local.yaml`, so it survives restarts without entering Git.
- Fixed ROI editing so periodic status polling cannot overwrite an in-progress drag; releasing the mouse now saves the ROI automatically.

## 2026-08-31 — Activity log

- Added a persistent activity feed in the web UI.
- Motion events, monitor startup, and ROI changes are written to ignored local `data/activity.jsonl` and exposed through `/activities`.
- The same feed will show the future overnight-training lifecycle, warnings, and outcomes.

## 2026-08-31 — Browser-only appliance mode

- Added optional password-protected web access with locally stored password hash and session secret.
- Added an update panel that checks the fixed Git remote and installs fast-forward-only updates before restarting the service.
- Added a restricted systemd service installer and sudo rule; no arbitrary browser-supplied shell command can be run.
- Added a one-time Raspberry Pi bootstrap script for installing prerequisites, cloning/updating the fixed repository, setting up uv, and enabling appliance mode.

## 2026-08-31 — Event gallery and annotations

- Added a local browser gallery for recent event images.
- Added bounding-box drawing and class labels for Asian hornet, European hornet, wasp, bee, other, empty, and uncertain.
- Stored annotations locally in ignored JSONL format for the future training-data export.

## 2026-08-31 — UX foundation

- Adopted Bootstrap 5 for a responsive, consistent dashboard, navigation, cards, forms, and login screen.
- Documented the UI responsibility and usability rules in the architecture guide.

## 2026-08-31 — Quality and security automation

- Extended CI with Python 3.11/3.13 checks, lockfile verification, branch coverage, and uv dependency audit.
- Added CodeQL security scanning and weekly Dependabot updates for uv dependencies and GitHub Actions.
- Added a documented quality policy and an incremental coverage-improvement plan.
