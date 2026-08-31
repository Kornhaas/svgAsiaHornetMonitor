# Asia Hornet Monitor

V0.1 is a Raspberry Pi camera application for collecting image data of activity near a hornet trap or observation site. It offers a live browser stream, configurable motion detection inside a region of interest (ROI), and local JPEG event bursts.

It deliberately contains no species classification or machine learning. The first goal is reliable data collection for a future training dataset.

## Features

- OpenCV capture from a USB webcam (default: `/dev/video0`)
- 1280 × 720 MJPEG camera configuration at 30 FPS
- Browser live stream at `http://<pi-address>:8000`
- ROI-only motion detection with a visible live status
- Timestamped event folders with a JPEG burst
- YAML configuration and modular camera, motion, event, and web components

## Dependency management

Dependencies are managed with [uv](https://docs.astral.sh/uv/), using the checked-in `pyproject.toml` and `uv.lock`. Install uv once on each development or target machine:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

The exact locked versions are installed with `uv sync`. To add a dependency later, use `uv add <package>` and commit both `pyproject.toml` and `uv.lock`.

## Raspberry Pi setup

On Raspberry Pi OS Lite 64-bit:

```bash
sudo apt update
sudo apt install -y curl libatlas-base-dev
git clone https://github.com/Kornhaas/svgAsiaHornetMonitor.git
cd svgAsiaHornetMonitor
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync --locked
```

Check that the webcam is available and supports the expected MJPEG mode:

```bash
v4l2-ctl --list-formats-ext --device /dev/video0
```

If `v4l2-ctl` is unavailable, install it with `sudo apt install v4l-utils`.

## Run

```bash
uv run hornet-monitor
```

Open `http://<raspberry-pi-ip>:8000` from a device on the same network. Stop with `Ctrl+C`.

## Configuration

Edit [`config/config.yaml`](config/config.yaml) before deployment:

- `camera.device`, `width`, `height`, and `fps` select the webcam mode.
- `motion.roi` is a rectangle in camera pixels.
- `motion.min_area` filters small changes such as sensor noise or light flicker.
- `motion.cooldown_seconds` limits how often an event starts.
- `events.burst_frames` and `burst_interval_seconds` control the saved JPEG series.

Saved events are created as `data/events/YYYY-MM-DD/HHMMSS_microseconds/frame_*.jpg`. This data, local config overrides, and logs are intentionally excluded from Git.

For a local machine where `/dev/video0` does not exist, set `camera.device: 0` in a separate `config/local.yaml` and run with `--config config/local.yaml` after copying the main config.

## Development

The source package is under `src/hornet_monitor`; the browser assets are under `web`. A minimal test run is:

```bash
uv run pytest
uv run ruff format --check .
uv run ruff check .
```

On a development PC, use the same repository and deploy with `git pull` on the Pi. VS Code Remote SSH is useful for directly testing the Pi camera, but Git remains the shared history.

Project decisions and milestones are recorded in [`LOGBOOK.md`](LOGBOOK.md). Guidance for Copilot and coding agents is in [`.github/copilot-instructions.md`](.github/copilot-instructions.md).

For system design and an AI-assisted change workflow, see [`docs/architecture.md`](docs/architecture.md) and [`docs/ai-collaboration.md`](docs/ai-collaboration.md).
