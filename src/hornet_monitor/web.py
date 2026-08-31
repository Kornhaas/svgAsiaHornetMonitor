"""Flask browser interface and MJPEG endpoint."""

from __future__ import annotations

import time
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
        return render_template("index.html")

    @app.get("/gallery")
    @require_login
    def gallery_page():
        return render_template("gallery.html")

    @app.get("/settings/roi")
    @require_login
    def roi_settings():
        return render_template("roi_settings.html")

    @app.get("/settings/camera")
    @require_login
    def camera_settings():
        return render_template("camera_settings.html")

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
        except ValueError as error:
            return jsonify(error=str(error)), 400

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
        except (TypeError, ValueError) as error:
            return jsonify(error=str(error)), 400

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
                "schedule": {"start_hour": "?", "stop_hour": "?"},
            }
            if training_status is None
            else training_status.overview()
        )
        return render_template("training.html", overview=overview)

    @app.post("/api/training/start")
    @require_login
    def start_training():
        if training_manager is None:
            return jsonify(error="Training is unavailable."), 503
        return jsonify(training_manager.start()), 202

    @app.get("/system")
    @require_login
    def system_page():
        return render_template("system.html")

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
        except ValueError as error:
            return jsonify(error=str(error)), 500

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
        return jsonify([] if gallery is None else gallery.events())

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
        except (FileNotFoundError, ValueError) as error:
            return jsonify(error=str(error)), 400

    @app.delete("/api/events/<path:event_id>")
    @require_login
    def remove_event(event_id):
        if delete_event is None:
            return jsonify(error="Event deletion is unavailable."), 503
        try:
            delete_event(event_id)
            return "", 204
        except (FileNotFoundError, ValueError) as error:
            return jsonify(error=str(error)), 404

    @app.get("/status")
    @require_login
    def get_status():
        return jsonify(status())

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
        except ValueError as error:
            return jsonify(error=str(error)), 400

    @app.get("/activities")
    @require_login
    def activities():
        return jsonify([] if activity_log is None else activity_log.recent())

    @app.post("/updates/check")
    @require_login
    def check_updates():
        return jsonify({"state": "disabled"} if update_manager is None else update_manager.check())

    @app.post("/updates/install")
    @require_login
    def install_updates():
        return jsonify(
            {"state": "disabled"} if update_manager is None else update_manager.install()
        )

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
