# Asia Hornet Monitor – Copilot instructions

## Project purpose

This project collects camera images and motion events for a future Vespa velutina (Asian hornet) training dataset. V0.1 must stay focused on stable image acquisition and event collection. Do not add species classification, machine learning, cloud services, or database infrastructure unless explicitly requested.

## Technology and commands

- Target: Raspberry Pi 4 B, Raspberry Pi OS Lite 64-bit, USB webcam at `/dev/video0`.
- Language: Python 3.11 or later.
- Dependency manager: `uv` only. Add packages with `uv add <package>` and commit both `pyproject.toml` and `uv.lock`.
- Run the application with `uv run hornet-monitor`.
- Run tests with `uv run pytest`.
- Run quality checks with `uv run ruff format --check .` and `uv run ruff check .`.

## Architecture

- Keep source code in `src/hornet_monitor/`.
- Keep responsibilities separate: `camera.py` captures frames, `motion.py` detects motion only in the ROI, `events.py` writes local event bursts, `web.py` serves the browser interface, and `main.py` composes the application.
- Keep configuration in `config/config.yaml`. Do not hard-code deployment-specific camera settings or paths.
- Browser templates and assets belong under `web/templates/` and `web/static/`.
- Event images belong in `data/events/` and must never be committed.

## Implementation expectations

- Prefer clear, small, typed Python functions and standard-library solutions where practical.
- Keep processing lightweight for the Raspberry Pi: avoid unnecessary copies, large dependencies, and CPU-heavy work in HTTP request handlers.
- Preserve the threaded design: capture and motion monitoring must not block MJPEG clients.
- Validate ROI bounds against each frame size and handle unavailable cameras without crashing the web server.
- Add or update focused unit tests for changed detection or event behavior.
- Run the test suite and `uv lock --check` before considering work complete.
- Update `LOGBOOK.md` for user-visible features, architectural decisions, deployment changes, and fixes.
- Before a non-trivial change, state the affected component, configuration impact, failure behavior, and tests to add. Use `docs/architecture.md` as the source of truth.

## Repository hygiene

- Do not commit `.venv/`, `data/events/`, captures, logs, credentials, or `config/local.yaml`.
- Do not edit `uv.lock` manually; regenerate it through uv.
- Keep README installation commands aligned with the actual uv workflow.
