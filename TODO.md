# Production readiness checklist

This checklist is kept in source control and records the implemented operating model and the remaining physical acceptance checks.

## Implemented

- [x] Initial camera-open failures keep the capture thread alive; reconnect retries use bounded exponential backoff.
- [x] Camera-offline, low-storage, and failed-training transitions are recorded; optional Telegram alerts use the configured rate limit.
- [x] Storage warning threshold, scheduled retention cleanup, and recursive ZIP backups for event images, annotations, background, and model versions.
- [x] Atomic local annotation replacements using a temporary file, `fsync`, and `os.replace`.
- [x] Versioned YOLO exports, deterministic splits, negative/empty images, split counts, and manifests.
- [x] Versioned model runs, latest-model activation/rollback, evaluation fields (precision, recall, mAP50, mAP50-95), and prediction history.
- [x] Night training starts only inside the configured time window, has a 06:00 deadline, and exposes epoch progress when YOLO writes `results.csv`.
- [x] Configuration validation, unit tests, Ruff, dependency lock validation, dependency audit, CodeQL workflow, and Dependabot.

## Required Pi acceptance checks

- [ ] Disconnect the USB camera before boot; confirm the browser stays reachable and reconnects after the camera is restored.
- [ ] Verify an overnight training run starts after 21:00 while dark, writes a versioned model, and stops by 06:00.
- [ ] Trigger a low-storage condition on a disposable test device; confirm cleanup, status warning, and optional Telegram alert.
- [ ] Create a backup and inspect the ZIP for `events/`, `models/`, annotation data, and background files.
- [ ] Verify a trained model detects an event and that its prediction appears under **Model & training**.

## Operational follow-up

- [ ] Raise test coverage from the current 53% to 60% after the Pi acceptance suite has been automated with camera fakes, then to 80% after hardware adapters are isolated further.
- [ ] If remote access is needed, deploy HTTPS via a reverse proxy or use a VPN; do not expose the Flask service directly to the internet.
