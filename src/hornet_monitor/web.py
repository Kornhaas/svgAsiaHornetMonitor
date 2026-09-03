"""Flask browser interface and MJPEG endpoint."""

from __future__ import annotations

import json
import time
from collections import Counter
from functools import wraps
from pathlib import Path

import cv2
from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from werkzeug.security import check_password_hash

from .gallery import ANIMAL_LABELS
from .i18n import translations


def create_app(
    camera,
    status,
    update_roi=None,
    activity_log=None,
    auth=None,
    update_manager=None,
    gallery=None,
    save_annotation=None,
    delete_event=None,
    training_status=None,
    background=None,
    event_frame=None,
    system_status=None,
    training_manager=None,
    update_camera=None,
    update_telegram=None,
    storage=None,
    prediction_history=None,
    manual_trigger=None,
):
    app = Flask(__name__, template_folder="../../web/templates", static_folder="../../web/static")
    auth = auth or {"enabled": False}
    if auth.get("enabled") and not all(
        auth.get(key) for key in ("username", "password_hash", "secret_key")
    ):
        raise ValueError(
            "Enabled web authentication requires username, password_hash, and secret_key."
        )
    app.secret_key = auth.get("secret_key", "development-only-secret")

    def gallery_events_with_suggestions(
        label: str | None = None, pending_only: bool = False
    ) -> list[dict]:
        """Attach the newest actionable model proposal to each unreviewed event frame.

        Predictions remain separate from annotations until a person confirms them in the
        gallery. This prevents a weak model from feeding its own errors back into training.
        """
        if gallery is None:
            return []
        event_options = {"limit": None} if pending_only else {}
        events = (
            gallery.events(**event_options)
            if label is None
            else gallery.events(label=label, **event_options)
        )
        if prediction_history is None:
            return [] if pending_only else events
        newest_by_image: dict[str, dict] = {}
        for prediction in prediction_history():
            image = prediction.get("image")
            box = prediction.get("box")
            if (
                isinstance(image, str)
                and image not in newest_by_image
                and prediction.get("label") in ANIMAL_LABELS
                and isinstance(prediction.get("confidence"), (int, float))
                and isinstance(box, dict)
                and all(isinstance(box.get(key), int) for key in ("x", "y", "width", "height"))
                and box["x"] >= 0
                and box["y"] >= 0
                and box["width"] > 0
                and box["height"] > 0
            ):
                newest_by_image[image] = prediction
        predicted_labels = Counter(prediction["label"] for prediction in newest_by_image.values())
        for event in events:
            event["suggestions"] = {
                frame: newest_by_image[frame]
                for frame in event["frames"]
                if frame not in event["reviewed_frames"] and frame in newest_by_image
            }
            proposals = list(event["suggestions"].values())
            if proposals:
                best = max(
                    proposals,
                    key=lambda proposal: (
                        proposal.get("best_in_burst", False),
                        proposal["confidence"],
                    ),
                )
                event["best_suggestion_image"] = best["image"]
                labels = {proposal["label"] for proposal in proposals}
                event["suggestion_priority"] = round(
                    (1 - best["confidence"])
                    + (0.5 if len(labels) > 1 else 0)
                    + (0.25 if not best.get("best_in_burst") else 0)
                    + (0.25 / predicted_labels[best["label"]]),
                    3,
                )
            else:
                event["best_suggestion_image"] = None
                event["suggestion_priority"] = -1
        events.sort(key=lambda event: event["suggestion_priority"], reverse=True)
        return [event for event in events if event["suggestions"]] if pending_only else events

    @app.context_processor
    def inject_i18n():
        language = session.get("language", "de")
        return {"language": language, "translations": translations(language)}

    @app.after_request
    def add_i18n(response):
        if response.mimetype != "text/html":
            return response
        language = session.get("language", "de")
        page = response.get_data(as_text=True).replace('lang="en"', f'lang="{language}"')
        for source, target in translations(language).items():
            page = page.replace(source, target)
        script = (
            f"<script>window.hornetTranslations={translations(language)!r};</script>"
            '<script src="/static/i18n.js"></script>'
        )
        response.set_data(page.replace("</body>", f"{script}</body>"))
        return response

    def require_login(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not auth.get("enabled") or session.get("authenticated"):
                return view(*args, **kwargs)
            if request.path == "/":
                return redirect(url_for("login"))
            return jsonify(error="Authentication required."), 401

        return wrapped

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if not auth.get("enabled"):
            return redirect(url_for("index"))
        error = None
        if request.method == "POST":
            if request.form.get("username") == auth["username"] and check_password_hash(
                auth["password_hash"], request.form.get("password", "")
            ):
                session["authenticated"] = True
                return redirect(url_for("index"))
            error = "Invalid username or password."
        return render_template("login.html", error=error)

    @app.post("/language/<language>")
    def set_language(language):
        if language not in {"de", "en"}:
            return jsonify(error="Unsupported language."), 400
        session["language"] = language
        return jsonify(language=language, translations=translations(language))

    @app.post("/logout")
    @require_login
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.get("/")
    @require_login
    def index():
        return render_template("index.html", active_page="monitor")

    @app.get("/gallery")
    @require_login
    def gallery_page():
        return render_template("gallery.html", active_page="gallery")

    @app.get("/settings/roi")
    @require_login
    def roi_settings():
        return render_template("roi_settings.html", active_page="roi")

    @app.get("/settings/camera")
    @require_login
    def camera_settings():
        return render_template("camera_settings.html", active_page="camera")

    @app.get("/api/cameras")
    @require_login
    def cameras():
        return jsonify([str(path) for path in Path("/dev").glob("video*")])

    @app.put("/api/camera")
    @require_login
    def set_camera():
        if update_camera is None:
            return jsonify(error="Camera editing is unavailable."), 503
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(error="Expected camera settings."), 400
        try:
            update_camera(payload)
            return jsonify(message="Camera saved; monitor is restarting."), 202
        except ValueError:
            return jsonify(error="Camera settings are invalid."), 400

    @app.put("/api/telegram")
    @require_login
    def set_telegram():
        if update_telegram is None:
            return jsonify(error="Telegram configuration is unavailable."), 503
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(error="Expected Telegram settings."), 400
        try:
            update_telegram(payload)
            return jsonify(message="Telegram settings saved; monitor is restarting."), 202
        except (TypeError, ValueError):
            return jsonify(error="Telegram settings are invalid."), 400

    @app.post("/api/backup")
    @require_login
    def backup():
        if storage is None:
            return jsonify(error="Backup is unavailable."), 503
        return jsonify(path=storage.backup()), 201

    @app.get("/training")
    @require_login
    def training_page():
        overview = (
            {
                "message": "Training status is unavailable.",
                "reviewed_images": 0,
                "annotations": 0,
                "minimum_annotations": 0,
                "ready": False,
                "labels": {},
                "dataset": {"splits": {"train": 0, "val": 0, "test": 0}},
                "models": [],
                "run": {},
                "schedule": {"start_hour": "?", "stop_hour": "?"},
            }
            if training_status is None
            else training_status.overview()
        )
        return render_template("training.html", overview=overview, active_page="training")

    @app.post("/api/training/start")
    @require_login
    def start_training():
        if training_manager is None:
            return jsonify(error="Training is unavailable."), 503
        return jsonify(training_manager.start()), 202

    @app.post("/api/models/<version>/activate")
    @require_login
    def activate_model(version):
        if training_manager is None:
            return jsonify(error="Model activation is unavailable."), 503
        try:
            model = training_manager.activate(version)
        except (ValueError, OSError, KeyError, json.JSONDecodeError):
            return jsonify(error="Model version is unavailable."), 404
        return jsonify(model=model), 200

    @app.get("/system")
    @require_login
    def system_page():
        return render_template("system.html", active_page="system")

    @app.get("/api/system-status")
    @require_login
    def get_system_status():
        return jsonify(
            {
                "device": {} if system_status is None else system_status(),
                "background": {"available": False, "updated_at": None}
                if background is None
                else background.status(),
                "update": {"state": "disabled"}
                if update_manager is None
                else update_manager._state,
            }
        )

    @app.post("/api/background")
    @require_login
    def update_background():
        if background is None or event_frame is None:
            return jsonify(error="Background capture is unavailable."), 503
        frame = event_frame()
        if frame is None:
            return jsonify(error="Camera frame is unavailable."), 503
        try:
            return jsonify(background=background.save(frame)), 201
        except ValueError:
            return jsonify(error="Background update failed."), 500

    @app.get("/api/events/<path:image_id>/proposals")
    @require_login
    def event_proposals(image_id):
        if gallery is None or background is None:
            return jsonify([])
        try:
            import cv2

            frame = cv2.imread(str(gallery.image_path(image_id)))
            return jsonify(background.proposals(frame))
        except (FileNotFoundError, ValueError):
            return jsonify([])

    @app.get("/api/events")
    @require_login
    def events():
        pending = request.args.get("pending")
        if pending not in {None, "1"}:
            return jsonify(error="Invalid pending filter."), 400
        try:
            return jsonify(
                gallery_events_with_suggestions(
                    request.args.get("label"), pending_only=pending == "1"
                )
            )
        except ValueError:
            return jsonify(error="Unknown annotation label."), 400

    @app.get("/api/annotations/<path:image_id>")
    @require_login
    def image_annotations(image_id):
        if gallery is None:
            return jsonify([])
        try:
            return jsonify(gallery.annotations_for(image_id))
        except (FileNotFoundError, ValueError):
            return jsonify([])

    @app.get("/api/dataset")
    @require_login
    def dataset_status():
        return jsonify({} if training_manager is None else training_manager.exporter.summary())

    @app.get("/api/predictions")
    @require_login
    def predictions():
        return jsonify([] if prediction_history is None else prediction_history())

    @app.post("/api/dataset/export")
    @require_login
    def export_dataset():
        if training_manager is None:
            return jsonify(error="Dataset export is unavailable."), 503
        summary = training_manager.exporter.summary()
        if not summary["boxes"]:
            return jsonify(error="At least one labelled animal box is required."), 400
        try:
            dataset = training_manager.exporter.export()
        except (OSError, ValueError):
            return jsonify(error="Dataset export failed."), 500
        return jsonify(dataset=dataset), 201

    @app.get("/event-image/<path:image_id>")
    @require_login
    def event_image(image_id):
        if gallery is None:
            return jsonify(error="Gallery is unavailable."), 503
        try:
            return send_file(gallery.image_path(image_id))
        except (FileNotFoundError, ValueError):
            return jsonify(error="Image not found."), 404

    @app.post("/api/annotations")
    @require_login
    def annotations():
        if save_annotation is None:
            return jsonify(error="Annotation storage is unavailable."), 503
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(error="Expected an annotation JSON object."), 400
        try:
            return jsonify(annotation=save_annotation(payload)), 201
        except (FileNotFoundError, ValueError):
            return jsonify(error="Annotation is invalid or its image is unavailable."), 400

    @app.post("/api/events/<path:event_id>/mark-empty")
    @require_login
    def mark_event_empty(event_id):
        if gallery is None:
            return jsonify(error="Gallery is unavailable."), 503
        try:
            return jsonify(frames=gallery.mark_unannotated_frames_empty(event_id)), 201
        except (FileNotFoundError, ValueError):
            return jsonify(error="Event is unavailable."), 404

    @app.delete("/api/events/<path:event_id>")
    @require_login
    def remove_event(event_id):
        if delete_event is None:
            return jsonify(error="Event deletion is unavailable."), 503
        try:
            delete_event(event_id)
            return "", 204
        except (FileNotFoundError, ValueError):
            return jsonify(error="Event was not found."), 404

    @app.get("/status")
    @require_login
    def get_status():
        return jsonify(status())

    @app.post("/api/events/trigger")
    @require_login
    def trigger_event():
        if manual_trigger is None:
            return jsonify(error="Manual event capture is unavailable."), 503
        try:
            result = manual_trigger()
        except (OSError, ValueError):
            app.logger.exception("Manual event capture failed")
            return jsonify(error="Manual event capture failed."), 500
        if result["state"] == "saved":
            return jsonify(result), 201
        if result["state"] == "cooldown":
            return jsonify(error=result["message"]), 429
        return jsonify(error=result["message"]), 503

    @app.put("/roi")
    @require_login
    def set_roi():
        if update_roi is None:
            return jsonify(error="ROI editing is unavailable."), 503
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(error="Expected an ROI JSON object."), 400
        try:
            return jsonify(roi=update_roi(payload))
        except ValueError:
            return jsonify(error="ROI settings are invalid."), 400

    @app.get("/activities")
    @require_login
    def activities():
        return jsonify([] if activity_log is None else activity_log.recent())

    @app.post("/updates/check")
    @require_login
    def check_updates():
        if update_manager is None:
            return jsonify({"state": "disabled"})
        try:
            return jsonify(update_manager.check())
        except Exception:
            app.logger.exception("Update check failed")
            return jsonify(error="Update check is temporarily unavailable."), 503

    @app.post("/updates/install")
    @require_login
    def install_updates():
        if update_manager is None:
            return jsonify({"state": "disabled"})
        try:
            return jsonify(update_manager.install())
        except Exception:
            app.logger.exception("Update installation request failed")
            return jsonify(error="Update installation is temporarily unavailable."), 503

    @app.get("/stream.mjpg")
    @require_login
    def stream():
        def generate():
            while True:
                frame = camera.get_frame()
                if frame is None:
                    time.sleep(0.1)
                    continue
                ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if ok:
                    yield (
                        b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + encoded.tobytes() + b"\r\n"
                    )
                time.sleep(0.03)

        return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

    return app
