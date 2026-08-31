# Asia Hornet Monitor

V0.1 is a Raspberry Pi camera application for collecting image data of activity near a hornet trap or observation site. It offers a live browser stream, configurable motion detection inside a region of interest (ROI), and local JPEG event bursts.

It deliberately contains no species classification or machine learning. The first goal is reliable data collection for a future training dataset.

## Features

- OpenCV capture from a USB webcam (default: `/dev/video0`)
- 1280 × 720 MJPEG camera configuration at 30 FPS
- Browser live stream at `http://<pi-address>:8000`
- ROI-only motion detection with a visible live status
- Visible, drag-adjustable ROI overlay with numeric controls in the browser
- ROI-cropped event images, excluding moving background outside the yellow rectangle
- Persistent activity log in the web UI for motion events and configuration changes
- Browser image gallery for reviewing events and saving labelled bounding boxes
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
sudo apt install -y curl
git clone https://github.com/Kornhaas/svgAsiaHornetMonitor.git
cd svgAsiaHornetMonitor
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv sync --locked --no-dev
```

`libatlas-base-dev` is deliberately not required. It is unavailable on current Raspberry Pi OS Trixie installations, and the project uses the OpenCV wheel installed by uv. YOLO/PyTorch are installed for local training and require substantial disk space and time on a Pi 4. The `export PATH=...` command makes the just-installed uv executable available in the current shell.

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

## Appliance mode: browser-only operation

For a new Raspberry Pi, run the one-time setup as the `hornet` user. It installs curl and Git, installs uv if needed, clones or updates this repository, creates the production environment, asks for one web password, and activates the service:

```bash
curl -LsSf https://raw.githubusercontent.com/Kornhaas/svgAsiaHornetMonitor/main/scripts/setup-pi.sh | bash
```

For an already-cloned project, install the service once from the project root instead:

```bash
bash scripts/install-service.sh
```

The installer asks once for a web password, enables service autostart, and configures the browser update button. After that, sign in at `http://hornet.local:8000` to operate the monitor, check for updates, and install updates. The update action uses fast-forward-only Git pulls, installs the locked runtime dependencies, records the result in the activity log, and restarts the service.

The installer is intentionally limited to `/home/hornet/svgAsiaHornetMonitor` and only grants the `hornet` user permission to restart this one service. Do not expose the monitor directly to the internet.

Installing an update restarts the monitor service and therefore briefly closes the camera stream. The browser waits eight seconds and reloads itself automatically; an interrupted stream also reconnects on its own.

## Configuration

Edit [`config/config.yaml`](config/config.yaml) before deployment:

- `camera.device`, `width`, `height`, and `fps` select the webcam mode.
- `motion.roi` is a rectangle in camera pixels.
- In the browser, draw a rectangle on the live image; it is saved automatically when you release the mouse. Alternatively enter `X`, `Y`, `Width`, and `Height`, then select **Save ROI**. The change takes effect immediately and is saved only to ignored `config/local.yaml` on that device.
- `motion.min_area` filters small changes such as sensor noise or light flicker.
- `motion.cooldown_seconds` limits how often an event starts.
- `events.burst_frames` and `burst_interval_seconds` control the saved JPEG series.
- `events.crop_to_roi` keeps saved gallery and training images limited to the ROI (enabled by default). The live stream remains full-frame so the ROI can still be adjusted comfortably.
- `training.minimum_annotations` defines the initial dataset threshold displayed in the UI. `training.start_hour` and `stop_hour` reserve the intended future overnight training window; they do not start training yet.
- `night_mode` estimates brightness from the saved ROI image. After `dark_seconds` below `dark_threshold`, motion capture pauses; it resumes only after `bright_threshold` is reached, avoiding rapid switching at dusk.

Saved events are created as `data/events/YYYY-MM-DD/HHMMSS_microseconds/frame_*.jpg`. This data, local config overrides, and logs are intentionally excluded from Git.

## Image gallery and manual labels

Select **Open image gallery** in the web UI to review recent event images. By default it displays only unreviewed events. Select an event, draw a box around the animal, choose a class, and save it; the gallery opens the next unreviewed event automatically. Labels are stored locally in `data/annotations.jsonl`; they will form the future YOLO training dataset and are not committed to Git.

The **ROI settings** page is the only page that can change the motion and event-image crop. The live monitor displays the ROI read-only. The **Model & training** page shows the number and distribution of local annotations, the model state, and the reserved 21:00–06:00 training window. It does not claim to train or classify until the separate training worker is implemented.

## Training and notifications

Reviewed animal boxes can be exported automatically into deterministic YOLO train/validation/test splits. When night mode starts and the configured number of labelled boxes is reached, the local bounded training worker starts; it is stopped at the configured morning deadline. The **Model & training** page can also start a run manually.

Reopening an already reviewed gallery image loads its saved boxes into the editable list. Remove incorrect entries, add replacements, then save the complete list; this atomically replaces that image's annotations.

The **Camera settings** page at `/settings/camera` selects a local `/dev/video*` device and stores its resolution/FPS in ignored `config/local.yaml`; saving restarts only the monitor service. The **System status** page configures optional Telegram review notifications. Tokens and chat IDs are likewise written only to `config/local.yaml`, never Git. Telegram sends a rate-limited event image for low-confidence predictions or a possible Asian hornet; it does not interrupt capture when offline.

## Background reference and multiple animals

Use the **System status** page at `/system` to capture a background reference while the ROI is empty. The reference is local and excluded from Git. In the gallery, draw and add one box per animal, then save all boxes together. **Suggest objects** compares an event to the reference with OpenCV and adds conservative `uncertain` proposals; always review, correct, or remove them before saving. Update the reference after moving the camera, changing the ROI, or a substantial lighting/background change.

**Delete event** asks for confirmation, then removes the selected event and all of its burst images. This is appropriate for test captures such as a hand in front of the camera and avoids keeping partial event bursts.

For a local machine where `/dev/video0` does not exist, create ignored `config/local.yaml` containing `camera: { device: 0 }`. It is automatically merged over the tracked base configuration at startup.

## Development

The source package is under `src/hornet_monitor`; the browser assets are under `web`. A minimal test run is:

```bash
uv run pytest
uv run ruff format --check .
uv run ruff check .
```

On a development PC, use the same repository and deploy with `git pull` on the Pi. VS Code Remote SSH is useful for directly testing the Pi camera, but Git remains the shared history.

Project decisions and milestones are recorded in [`LOGBOOK.md`](LOGBOOK.md). Guidance for Copilot and coding agents is in [`.github/copilot-instructions.md`](.github/copilot-instructions.md).

## Languages

The web UI is available in German and English. Choose **Deutsch** or **English** with the language picker in the lower-right corner; the choice is stored in the browser session. Translation strings are local in `src/hornet_monitor/i18n.py`, so adding another language does not require a cloud service.

For system design and an AI-assisted change workflow, see [`docs/architecture.md`](docs/architecture.md) and [`docs/ai-collaboration.md`](docs/ai-collaboration.md).

Quality checks, security scans, dependency updates, and the GitHub branch-protection recommendations are documented in [`docs/quality.md`](docs/quality.md).
