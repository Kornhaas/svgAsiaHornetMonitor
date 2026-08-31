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
                    EventWriter ─► data/events/YYYY-MM-DD/...
                           │
                           └──────────► ActivityLog ─► data/activity.jsonl ─► Web /activities

Event images ─► Gallery + annotation UI ─► data/annotations.jsonl

config/config.yaml ─► main.py (composition and runtime state) ─► Web /status
                                                          └──► UpdateManager ─► Git + systemd restart
```

## Component contracts

| Component | Owns | Must not own |
| --- | --- | --- |
| `camera.py` | Opening and reading a camera; thread-safe latest-frame access | Motion rules, HTTP, file storage |
| `motion.py` | ROI validation and frame-to-motion decision | Saving data, starting threads, web state |
| `events.py` | Event folder naming, cooldown, JPEG burst writing | Camera setup, motion thresholds |
| `web.py` | HTML, MJPEG response, JSON status endpoint | Direct camera reads or event decisions |
| `updates.py` | Fast-forward-only update check/install and service restart | Arbitrary command execution or user-supplied paths |
| `main.py` | Configuration loading and component wiring | Complex image processing or presentation |

## Runtime behavior

1. `main.py` reads YAML configuration and starts one camera capture thread.
2. The monitor loop obtains copies of the latest frame and asks `MotionDetector` to inspect only the configured ROI.
3. A positive decision asks `EventWriter` to save the first JPEG immediately and remaining burst frames asynchronously. Cooldown prevents event floods.
4. The browser consumes the same latest frame and a read-only status snapshot. It never opens the camera itself. It may update the ROI through the explicit `/roi` endpoint; `MotionDetector` validates it and resets its background model.

## Configuration boundary

`config/config.yaml` is the committed baseline. Machine-specific changes belong in ignored `config/local.yaml`, which is automatically merged over the baseline at startup. Paths in the standard configuration are relative to the repository root, so the application should be started from that root.

## Operations and updates

Appliance mode uses `hornet-monitor.service` under systemd. The web UI is password-protected after `scripts/install-service.sh` has configured ignored local credentials. The updater accepts no user-supplied Git URL, command, path, or service name: it updates only the configured repository by `git pull --ff-only`, runs `uv sync --locked --no-dev`, then restarts only `hornet-monitor.service` through a narrowly scoped sudo rule.

`scripts/setup-pi.sh` is the one-time bootstrap for a new Pi. It is deliberately fixed to the `hornet` user and this repository; it does not accept remote URLs or arbitrary installation paths.

## Future classifier boundary

When classification is requested, add `classifier.py` behind an explicit interface such as `classify(frame) -> ClassificationResult`. Run it only after an event is created, ideally in a bounded worker queue. Do not put inference in the camera thread, MJPEG generator, or motion detector.
