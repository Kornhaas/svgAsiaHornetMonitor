"""Flask browser interface and MJPEG endpoint."""

from __future__ import annotations

import time
from functools import wraps

import cv2
from flask import Flask, Response, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash


def create_app(camera, status, update_roi=None, activity_log=None, auth=None, update_manager=None):
    app = Flask(__name__, template_folder="../../web/templates", static_folder="../../web/static")
    auth = auth or {"enabled": False}
    if auth.get("enabled") and not all(
        auth.get(key) for key in ("username", "password_hash", "secret_key")
    ):
        raise ValueError(
            "Enabled web authentication requires username, password_hash, and secret_key."
        )
    app.secret_key = auth.get("secret_key", "development-only-secret")

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

    @app.post("/logout")
    @require_login
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.get("/")
    @require_login
    def index():
        return render_template("index.html")

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
