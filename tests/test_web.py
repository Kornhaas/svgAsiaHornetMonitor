from werkzeug.security import generate_password_hash

from hornet_monitor.web import create_app


def test_index_and_status_are_available():
    app = create_app(camera=None, status=lambda: {"motion": False, "camera_error": None})
    client = app.test_client()

    index = client.get("/")
    status = client.get("/status")

    assert index.status_code == 200
    assert b"Asia Hornet Monitor" in index.data
    assert b"favicon.svg" in index.data
    assert status.get_json() == {"camera_error": None, "motion": False}


def test_roi_endpoint_validates_and_forwards_updates():
    saved = []
    app = create_app(
        camera=None, status=lambda: {}, update_roi=lambda roi: saved.append(roi) or roi
    )
    client = app.test_client()

    response = client.put("/roi", json={"x": 10, "y": 20, "width": 30, "height": 40})

    assert response.status_code == 200
    assert response.get_json()["roi"] == {"height": 40, "width": 30, "x": 10, "y": 20}
    assert saved == [{"x": 10, "y": 20, "width": 30, "height": 40}]


def test_activities_endpoint_returns_recent_entries():
    entries = [{"event": "motion_event", "message": "Motion event saved"}]
    app = create_app(
        camera=None,
        status=lambda: {},
        activity_log=type("Log", (), {"recent": lambda self: entries})(),
    )

    assert app.test_client().get("/activities").get_json() == entries


def test_enabled_auth_protects_monitor_and_accepts_valid_login():
    auth = {
        "enabled": True,
        "username": "hornet",
        "password_hash": generate_password_hash("secret"),
        "secret_key": "test-secret",
    }
    app = create_app(camera=None, status=lambda: {}, auth=auth)
    client = app.test_client()

    assert client.get("/").status_code == 302
    assert client.get("/status").status_code == 401
    assert (
        client.post("/login", data={"username": "hornet", "password": "secret"}).status_code == 302
    )
    assert client.get("/status").status_code == 200


def test_gallery_page_and_events_endpoint_are_available():
    gallery = type("Gallery", (), {"events": lambda self: [{"id": "event"}]})()
    app = create_app(camera=None, status=lambda: {}, gallery=gallery)
    client = app.test_client()

    assert client.get("/gallery").status_code == 200
    assert client.get("/api/events").get_json() == [{"id": "event"}]


def test_roi_settings_and_training_pages_are_available():
    training = type(
        "Training",
        (),
        {
            "overview": lambda self: {
                "message": "No model has been trained yet.",
                "reviewed_images": 2,
                "annotations": 2,
                "minimum_annotations": 50,
                "ready": False,
                "labels": {},
                "schedule": {"start_hour": 21, "stop_hour": 6},
            }
        },
    )()
    app = create_app(camera=None, status=lambda: {}, training_status=training)
    client = app.test_client()

    assert client.get("/settings/roi").status_code == 200
    training_page = client.get("/training")
    assert training_page.status_code == 200
    assert b"No model yet" in training_page.data


def test_event_deletion_endpoint_forwards_the_event_id():
    deleted = []
    app = create_app(
        camera=None, status=lambda: {}, delete_event=lambda event_id: deleted.append(event_id)
    )

    assert app.test_client().delete("/api/events/2026-08-31/event").status_code == 204
    assert deleted == ["2026-08-31/event"]


def test_language_selection_is_stored_in_the_browser_session():
    app = create_app(camera=None, status=lambda: {})
    client = app.test_client()

    assert client.post("/language/en").get_json()["language"] == "en"
    assert b'lang="en"' in client.get("/").data
    assert client.post("/language/fr").status_code == 400


def test_camera_and_training_controls_forward_safe_payloads():
    saved_camera, training = (
        [],
        type("Training", (), {"start": lambda self: {"state": "waiting"}})(),
    )
    app = create_app(
        camera=None,
        status=lambda: {},
        update_camera=lambda settings: saved_camera.append(settings),
        training_manager=training,
    )
    client = app.test_client()

    assert client.get("/settings/camera").status_code == 200
    assert (
        client.put(
            "/api/camera",
            json={"device": "/dev/video0", "width": 1280, "height": 720, "fps": 30, "mjpeg": True},
        ).status_code
        == 202
    )
    assert saved_camera[0]["device"] == "/dev/video0"
    assert client.post("/api/training/start").get_json()["state"] == "waiting"
