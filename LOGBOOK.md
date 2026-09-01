# Project logbook

This log records implementation milestones and decisions. Add a dated entry whenever behavior, deployment, or architecture changes in a way that matters to future work.

## 2026-09-01 — Complete Raspberry Pi bootstrap dependencies

- Updated `scripts/setup-pi.sh` to install the required OS packages for camera diagnostics and OpenCV, add the service user to the `video` group, and install all locked production Python dependencies.
- Documented that the bootstrap enables and starts `hornet-monitor.service`, so the monitor starts automatically following each Raspberry Pi reboot.

## 2026-09-01 — Consistent application navigation

- Introduced one shared Bootstrap base template for all authenticated application pages.
- Added direct navigation to live monitor, gallery, ROI settings, model training, system status, and camera settings, with the current page marked as active.
- Kept the login page intentionally separate because it is shown before authentication.
- Added a prominent System status shortcut next to the monitor status on the start page.

## 2026-09-01 — Local YOLO training toolkit

- Added self-contained Windows/local-PC scripts for dataset export, training, and validation below `training/`.
- Kept local experiment outputs separate from Pi-managed model versions so manual work cannot interrupt capture or activate an unreviewed model.
- Documented uv-only setup, Pi data transfer, GPU detection, reproducible commands, and the small-dataset limitation.

## 2026-09-01 — Update error handling hardening

- Removed subprocess and unexpected update-manager exception details from browser/API responses and activity entries.
- Kept internal exception logging on the server and added regression tests for both web update endpoints.

## 2026-09-01 — Guarded runtime-data reset

- Added a confirmation-gated script to remove locally collected images and analysis data for a fresh collection phase.
- Models and backups require separate explicit options, preventing an accidental loss of trained models or recovery archives.

## 2026-09-01 — Camera focus tuning guidance

- Documented the optional V4L2 workflow to use autofocus during installation, retain its sharp focus value, and lock manual focus during normal monitoring.

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

## 2026-08-31 — Fast gallery review

- Added reviewed status and an unreviewed-only gallery filter.
- Saving an annotation advances to the next unreviewed event.
- Added confirmed whole-event deletion for unusable test captures, including their annotations.

## 2026-08-31 — Quality and security automation

- Extended CI with Python 3.11/3.13 checks, lockfile verification, branch coverage, and uv dependency audit.
- Added CodeQL security scanning and weekly Dependabot updates for uv dependencies and GitHub Actions.
- Added a documented quality policy and an incremental coverage-improvement plan.

## 2026-08-31 — Background-free event captures

- Reused the existing motion ROI as the event-image crop, so moving trees or other scenery outside the yellow rectangle cannot create gallery or training-image content.
- Kept the live stream full-frame for comfortable ROI adjustment; only newly captured event burst images are cropped.
- Added a bounds-safe frame transformation with unit tests. The current ROI is read for every burst frame, so browser ROI changes apply immediately to subsequent events.

## 2026-08-31 — Safer ROI and training visibility

- Moved ROI editing to a dedicated browser page; the live monitor now displays the yellow ROI as read-only.
- Added a model-and-training status page that reports reviewed images, annotation totals, label distribution, the initial readiness threshold, and the planned 21:00–06:00 window.
- Kept training explicitly unimplemented: the page cannot misrepresent dataset collection as a trained or running model.

## 2026-08-31 — Multi-animal review and operational status

- Extended gallery storage to accept and replace multiple labelled boxes for one image.
- Added explicit ROI background capture and OpenCV difference proposals, stored locally and marked uncertain until reviewed.
- Added a local system-status page for background timestamp, disk space, CPU load, memory load, and the last code-update state.

## 2026-08-31 — German and English UI

- Added a local, session-based language selector with German as the default and English as an alternative.
- Kept the translation catalogue in source control and added no cloud translation dependency.

## 2026-08-31 — Resilient stream after updates

- Added automatic page reload after a browser-initiated service update and MJPEG reconnect handling after an interrupted stream.

## 2026-08-31 — Local training and appliance controls

- Added deterministic YOLO dataset export with train/validation/test splits, a deadline-bounded overnight training process, and asynchronous post-event prediction.
- Added optional, rate-limited Telegram review notifications with credentials stored only in local configuration.
- Added camera selection/settings, camera reconnect attempts, local metadata backups, configuration validation, and storage-warning state.

## 2026-08-31 — Editable reviewed annotations

- Gallery now reloads saved boxes when revisiting an image, allowing labels and boxes to be corrected as one replacement set.

## 2026-08-31 — Inner trigger and outer image regions

- Added a separate inner motion-trigger ROI inside the outer saved-image ROI.
- An event now starts only in the inner rectangle while the complete outer area is stored for classification and training context.

## 2026-08-31 — Image-based night mode

- Added ROI brightness measurement with a 20-minute sustained-darkness timer and separate bright/dark thresholds.
- Night mode pauses motion capture and records start/end transitions; daylight resets the motion background before capture resumes.

## 2026-08-31 — Direct image-region editing

- Made both the outer image ROI and the inner trigger ROI visible on the ROI settings camera preview.
- Added an explicit drawing-mode control: yellow edits the saved image area and blue edits the delayed trigger area; drawing saves the matching rectangle directly while retaining numeric precision fields.

## 2026-08-31 — Manual YOLO export

- Added an explicit, browser-operated versioned YOLO dataset export on the model and training page.
- The UI reports the resulting local directory and box count; exporting does not start the training worker.

## 2026-08-31 — Gallery review workflow

- Restored visual event thumbnails in the review list and added clear reviewed/unreviewed badges.
- The default view now hides reviewed events, advances to the next unreviewed event after saving, and offers an explicit filter to revisit reviewed images.

## 2026-08-31 — CodeQL path and error handling remediation

- Restricted gallery file access to canonical event-image identifiers before constructing a filesystem path, rejecting traversal and alternate path encodings.
- Replaced API responses that exposed exception text with stable client-safe error messages and added regression tests for both controls.

## 2026-09-01 — Correct ROI drawing dimensions

- Corrected the ROI editor to use the camera dimensions provided by the monitor status API instead of a nonexistent frame object.
- Prevented a plain click from saving a one-pixel rectangle.

## 2026-09-01 — Production operations and model lifecycle

- Added bounded camera reconnect after initial and later failures, operational Telegram alerts, storage retention cleanup, and complete recursive backups.
- Made annotation replacement crash-safe with atomic local writes.
- Added versioned model runs, model activation, YOLO evaluation metrics, prediction history, and time-windowed overnight training progress.
- Added the maintained `TODO.md` production-readiness and Raspberry Pi acceptance checklist.

## 2026-09-01 — Safer gallery default

- The image-gallery class selector now defaults to **Empty**, preventing accidental Asian-hornet annotations on blank event images.

## 2026-09-01 — Imported-model status resilience

- Made the model-and-training page tolerate locally imported model manifests that do not yet contain Pi-side evaluation metrics.

## 2026-09-01 — Active model visibility

- The training page now identifies the active model version and marks it clearly in the version table.

## 2026-09-01 — Numbered gallery proposals

- Gallery boxes and their annotation-list entries now share stable visible numbers for faster proposal review.

## 2026-09-01 — Isolated Pi inference

- Moved YOLO inference into a single spawned worker process so a native model crash cannot restart camera monitoring or the web UI.
- Replaced the unstable Ultralytics AutoBackend inference path with the verified direct YOLO forward pass and NMS path on the Pi.
- Limited the isolated inference worker to one low-priority CPU thread so new events do not monopolise the Pi while the gallery is in use.

## 2026-09-01 — Empty burst-frame review

- Saving an empty selected frame now marks all remaining unannotated frames of that event as empty without overwriting reviewed animal frames.

## 2026-09-01 — Active-learning review inbox

- Persisted image-space detection boxes and active model versions alongside isolated post-event predictions.
- Added a gallery filter and one-click, human-confirmed model-suggestion workflow; predictions remain separate from annotations until saved.
- Added annotation provenance (`manual` or `model_confirmed`) so exported training data remains auditable and a weak model cannot self-label future training data.

## 2026-09-01 — Burst-based active learning

- Moved post-event model inference to the completed burst so a single isolated worker evaluates every saved frame and selects the strongest proposal.
- Added a priority inbox for low-confidence, rare-class, and inconsistent burst predictions; model boxes render as cyan `AI` overlays before confirmation.
- Added feedback, confidence-calibration, class-balance, brightness-drift, and per-model quality evidence to the Model & Training page.
- Added an explicitly disabled-by-default automatic-acceptance policy. It can only label an allowed class after the configured confidence, sample-count, and observed-precision gates are met.

## 2026-09-01 — Dark event previews

- New events now store their measured brightness in local event metadata.
- Gallery cards hide a thumbnail below brightness 30 and show a clear night-mode indication instead, avoiding wasted preview loading for dark captures.

## 2026-09-01 — Immediate dark live-preview protection

- The live monitor now hides the MJPEG preview immediately below brightness 30 and closes its stream connection to save browser and Pi work.
- Motion capture still waits for the configured sustained-darkness period before entering the real night mode; the UI distinguishes this pending state from the active capture pause.

## 2026-09-01 — Training-status interaction

- The training start action now changes immediately to a disabled running state and the page refreshes periodically while the job is active, keeping epoch progress and completion state visible without accidental duplicate starts.

## 2026-09-01 — Training-worker diagnostics

- Failed Pi training runs now retain the worker exit code and display a safe signal name such as `SIGILL`, making native-library failures distinguishable from normal Python errors without exposing stack traces in the web UI.

## 2026-09-01 — Pi-safe YOLO training setup

- Disabled Ultralytics automatic mixed-precision validation for Pi CPU training. The check uses the same high-level inference route that is unstable on the target ARM build, while AMP provides no benefit for CPU-only runs.
- The Pi training worker now also suppresses Ultralytics model profiling during its internal model rebuild; a direct eight-class model build is verified on the Pi, while the profiling-enabled route terminates with `SIGILL` before training begins.
- Fatal-signal tracing is enabled only in the isolated training process, so any remaining native `SIGILL` failure records its Python call site in the systemd journal without affecting the monitor process or web UI.
