"""Flask browser interface and MJPEG endpoint."""

from __future__ import annotations

import time

import cv2
from flask import Flask, Response, jsonify, render_template


def create_app(camera, status):
    app = Flask(__name__, template_folder="../../web/templates", static_folder="../../web/static")

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/status")
    def get_status():
        return jsonify(status())

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
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + encoded.tobytes() + b"\r\n"
                time.sleep(0.03)
        return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

    return app
