# Architecture

## Scope and quality goals

V0.1 reliably collects motion-triggered image sequences from a USB camera on a Raspberry Pi. It must remain observable, recover gracefully from a missing camera, and write images locally without blocking the browser live stream.

The system is intentionally not a hornet classifier yet. A later classifier must consume saved event images through a separate module and must not alter the capture pipeline's reliability.

## Component map

```text
USB webcam (/dev/video0)
          │
          ▼
     Camera (one capture thread)
       ├──────────► Web /stream.mjpg ─► browser
       └──────────► MotionDetector (ROI only)
                           │ motion event
                           ▼
                 ROI frame crop ─► EventWriter ─► data/events/YYYY-MM-DD/...
                           │
                           └──────────► ActivityLog ─► data/activity.jsonl ─► Web /activities

Event images ─► Gallery + annotation UI ─► data/annotations.jsonl
                                              │
                                              └──► TrainingStatus ─► Web /training

ROI frame ─► BackgroundReference ─► data/background.jpg ─► OpenCV proposals ─► Gallery review

config/config.yaml ─► main.py (composition and runtime state) ─► Web /status
                                                          └──► UpdateManager ─► Git + systemd restart
```

## Component contracts

| Component | Owns | Must not own |
| --- | --- | --- |
| `camera.py` | Opening and reading a camera; thread-safe latest-frame access | Motion rules, HTTP, file storage |
| `motion.py` | ROI validation and frame-to-motion decision | Saving data, starting threads, web state |
| `frames.py` | Bounds-safe ROI crop for event and training frames | Motion decisions, camera access, file writes |
| `events.py` | Event folder naming, cooldown, JPEG burst writing | Camera setup, motion thresholds |
| `training.py` | Read-only annotation counts and planned model status | Training execution, camera processing, HTTP |
| `background.py` | Explicit reference capture and conservative proposal boxes | Automatic background updates or final classification |
| `system_status.py` | Dependency-free device-health snapshot | System control or configuration changes |
| `web.py` | HTML, MJPEG response, JSON status endpoint | Direct camera reads or event decisions |
| `updates.py` | Fast-forward-only update check/install and service restart | Arbitrary command execution or user-supplied paths |

## User-interface guidelines

The browser UI uses Bootstrap 5 for responsive layout and accessible controls, with a small local stylesheet only for camera overlays and project-specific presentation. Keep navigation consistent across the live monitor, gallery, login, future training, and activity views. UI actions must map to an explicit server endpoint and provide a visible success or failure message.
| `main.py` | Configuration loading and component wiring | Complex image processing or presentation |

## Runtime behavior

1. `main.py` reads YAML configuration and starts one camera capture thread.
2. The monitor loop obtains copies of the latest frame and asks `MotionDetector` to inspect only the configured ROI.
3. A positive decision crops the saved frame to the current ROI when `events.crop_to_roi` is enabled, then asks `EventWriter` to save the first JPEG immediately and remaining ROI-cropped burst frames asynchronously. Cooldown prevents event floods. The live stream is always the original full camera frame.
4. The live-monitor browser page consumes the same latest frame and a read-only status snapshot. It never opens the camera itself. Only the explicit ROI settings page may update the ROI through `/roi`; `MotionDetector` validates it and resets its background model.
5. The model-and-training page reads local annotation metadata through `TrainingStatus`. It does not start training, perform inference, or modify the capture pipeline.
6. The user may explicitly capture a cropped ROI background frame. Gallery proposals use only a difference against this reference and remain `uncertain` until a user confirms their class.

## Configuration boundary

`config/config.yaml` is the committed baseline. Machine-specific changes belong in ignored `config/local.yaml`, which is automatically merged over the baseline at startup. Paths in the standard configuration are relative to the repository root, so the application should be started from that root.

## Operations and updates

Appliance mode uses `hornet-monitor.service` under systemd. The web UI is password-protected after `scripts/install-service.sh` has configured ignored local credentials. The updater accepts no user-supplied Git URL, command, path, or service name: it updates only the configured repository by `git pull --ff-only`, runs `uv sync --locked --no-dev`, then restarts only `hornet-monitor.service` through a narrowly scoped sudo rule.

`scripts/setup-pi.sh` is the one-time bootstrap for a new Pi. It is deliberately fixed to the `hornet` user and this repository; it does not accept remote URLs or arbitrary installation paths.

## Training and classifier boundary

`dataset.py` is the only component that turns confirmed gallery boxes into YOLO data. `trainer.py` owns a separate, deadline-bounded process; `predictor.py` runs only after an event has been saved, in its own thread. `notifier.py` receives only prediction summaries and cannot block camera, motion, event writing, or the web UI. A missing or failed model must degrade to collection-only mode.
