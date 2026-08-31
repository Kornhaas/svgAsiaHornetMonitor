"""Flask browser interface and MJPEG endpoint."""

from __future__ import annotations

import time

import cv2
from flask import Flask, Response, jsonify, render_template, request


def create_app(camera, status, update_roi=None):
    app = Flask(__name__, template_folder="../../web/templates", static_folder="../../web/static")

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/status")
    def get_status():
        return jsonify(status())

    @app.put("/roi")
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

    @app.get("/stream.mjpg")
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
