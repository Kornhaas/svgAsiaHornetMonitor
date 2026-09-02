from pathlib import Path

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
    assert b'href="/system"' in index.data
    assert b'id="manual-trigger"' in index.data
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


def test_manual_trigger_forwards_capture_and_reports_unavailable_states():
    captured = []
    client = create_app(
        camera=None,
        status=lambda: {},
        manual_trigger=lambda: (
            captured.append(True)
            or {"state": "saved", "message": "Manual event saved.", "event": "event"}
        ),
    ).test_client()

    response = client.post("/api/events/trigger")

    assert response.status_code == 201
    assert response.get_json()["event"] == "event"
    assert captured == [True]
    unavailable = (
        create_app(camera=None, status=lambda: {}).test_client().post("/api/events/trigger")
    )
    assert unavailable.status_code == 503

    cooldown = (
        create_app(
            camera=None,
            status=lambda: {},
            manual_trigger=lambda: {"state": "cooldown", "message": "Wait."},
        )
        .test_client()
        .post("/api/events/trigger")
    )
    assert cooldown.status_code == 429


def test_api_validation_does_not_expose_internal_exception_details():
    app = create_app(
        camera=None,
        status=lambda: {},
        update_roi=lambda _roi: (_ for _ in ()).throw(ValueError("/private/config.yaml")),
    )

    response = app.test_client().put("/roi", json={"x": 1})

    assert response.status_code == 400
    assert response.get_json() == {"error": "ROI settings are invalid."}


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
    login = client.get("/login")
    assert b'autocomplete="username"' in login.data
    assert b'autocomplete="current-password"' in login.data
    assert (
        client.post("/login", data={"username": "hornet", "password": "secret"}).status_code == 302
    )
    assert client.get("/status").status_code == 200


def test_gallery_page_and_events_endpoint_are_available():
    gallery = type("Gallery", (), {"events": lambda self: [{"id": "event"}]})()
    app = create_app(camera=None, status=lambda: {}, gallery=gallery)
    client = app.test_client()

    gallery_page = client.get("/gallery")
    assert gallery_page.status_code == 200
    assert b'id="event-filter"' in gallery_page.data
    assert b'id="event-frames"' in gallery_page.data
    assert b'id="annotation-boxes"' in gallery_page.data
    assert b'<option value="empty" selected' in gallery_page.data
    assert b"Reviewed events with animals" in gallery_page.data
    assert client.get("/api/events").get_json() == [{"id": "event"}]


def test_events_endpoint_exposes_only_actionable_unreviewed_model_suggestions():
    event = {
        "id": "2026-09-01/123000_000001",
        "image": "2026-09-01/123000_000001/frame_000.jpg",
        "frames": ["2026-09-01/123000_000001/frame_000.jpg"],
        "reviewed_frames": [],
    }
    gallery = type("Gallery", (), {"events": lambda self: [event.copy()]})()
    prediction = {
        "image": event["image"],
        "label": "fleshfly",
        "confidence": 0.88,
        "box": {"x": 10, "y": 20, "width": 30, "height": 40},
        "model_version": "20260901_145318",
    }
    client = create_app(
        camera=None, status=lambda: {}, gallery=gallery, prediction_history=lambda: [prediction]
    ).test_client()

    assert client.get("/api/events").get_json()[0]["suggestions"] == {event["image"]: prediction}

    event["reviewed_frames"] = [event["image"]]
    assert client.get("/api/events").get_json()[0]["suggestions"] == {}


def test_roi_settings_and_training_pages_are_available():
    training = type(
        "Training",
        (),
        {
            "overview": lambda self: {
                "message": "No model has been trained yet.",
                "state": "idle",
                "reviewed_images": 2,
                "annotations": 2,
                "minimum_annotations": 50,
                "ready": False,
                "labels": {},
                "dataset": {"splits": {"train": 0, "val": 0, "test": 0}},
                "models": [],
                "run": {},
                "schedule": {"start_hour": 21, "stop_hour": 6},
            }
        },
    )()
    app = create_app(camera=None, status=lambda: {}, training_status=training)
    client = app.test_client()

    roi_page = client.get("/settings/roi")
    assert roi_page.status_code == 200
    assert b'id="outer-box"' in roi_page.data
    assert b'id="trigger-box"' in roi_page.data
    assert b"Draw image ROI" in roi_page.data
    roi_script = Path(app.static_folder) / "roi.js"
    assert "width: status.frame_width" in roi_script.read_text(encoding="utf-8")
    assert "[key, Number(value)]" in roi_script.read_text(encoding="utf-8")
    gallery_script = Path(app.static_folder) / "gallery.js"
    assert 'items = [{ label: "empty", box: null }]' in gallery_script.read_text(encoding="utf-8")
    assert 'if (box && label !== "empty")' in gallery_script.read_text(encoding="utf-8")
    assert "selectedFrame" in gallery_script.read_text(encoding="utf-8")
    assert "reloadSelectedEvent" in gallery_script.read_text(encoding="utf-8")
    assert "pointercancel" in gallery_script.read_text(encoding="utf-8")
    assert "Drag to draw a rectangle." in gallery_script.read_text(encoding="utf-8")
    assert "renderSavedBoxes" in gallery_script.read_text(encoding="utf-8")
    assert "annotation-box-number" in gallery_script.read_text(encoding="utf-8")
    assert "async function saveAnnotations" in gallery_script.read_text(encoding="utf-8")
    assert "await saveAnnotations()" in gallery_script.read_text(encoding="utf-8")
    assert "removeConfirmedProposalDuplicates" in gallery_script.read_text(encoding="utf-8")
    assert "intersection / union >= 0.5" in gallery_script.read_text(encoding="utf-8")
    assert "classifySingleProposal(label)" in gallery_script.read_text(encoding="utf-8")
    assert "uncertain.length !== 1" in gallery_script.read_text(encoding="utf-8")
    assert b"Accept and save suggestion" in client.get("/gallery").data
    training_page = client.get("/training")
    assert training_page.status_code == 200
    assert "Trainingsstatus" in training_page.get_data(as_text=True)


def test_training_page_renders_imported_model_without_evaluation():
    training = type(
        "Training",
        (),
        {
            "overview": lambda self: {
                "message": "Imported model is ready.",
                "state": "idle",
                "reviewed_images": 0,
                "annotations": 0,
                "minimum_annotations": 50,
                "ready": False,
                "labels": {},
                "dataset": {"splits": {"train": 0, "val": 0, "test": 0}},
                "models": [{"version": "20260901_145318", "evaluation": {}}],
                "active_model": "20260901_145318",
                "run": {},
                "schedule": {"start_hour": 21, "stop_hour": 6},
            }
        },
    )()

    response = (
        create_app(camera=None, status=lambda: {}, training_status=training)
        .test_client()
        .get("/training")
    )

    assert response.status_code == 200
    assert b"20260901_145318" in response.data
    assert b"Active model:" in response.data


def test_training_page_disables_start_button_while_job_is_running():
    training = type(
        "Training",
        (),
        {
            "overview": lambda self: {
                "message": "Training started.",
                "state": "running",
                "reviewed_images": 60,
                "annotations": 60,
                "minimum_annotations": 50,
                "ready": True,
                "labels": {},
                "dataset": {"splits": {"train": 42, "val": 12, "test": 6}},
                "models": [],
                "run": {"progress": {"epochs_completed": 3, "epochs_total": 30, "percent": 10}},
                "schedule": {"start_hour": 21, "stop_hour": 6},
            }
        },
    )()

    page = (
        create_app(camera=None, status=lambda: {}, training_status=training)
        .test_client()
        .get("/training")
    )
    text = page.get_data(as_text=True)

    assert page.status_code == 200
    assert 'id="start" class="btn btn-warning" disabled aria-disabled="true"' in text
    assert "Training running" in text
    assert "setTimeout(() => location.reload(), 5000)" in text


def test_application_pages_share_the_primary_navigation():
    app = create_app(camera=None, status=lambda: {})
    client = app.test_client()

    for path in ("/", "/gallery", "/settings/roi", "/settings/camera", "/training", "/system"):
        response = client.get(path)

        assert response.status_code == 200
        assert b'aria-label="Primary navigation"' in response.data
        assert b'href="/gallery"' in response.data
        assert b'href="/settings/roi"' in response.data
        assert b'href="/training"' in response.data
        assert b'href="/system"' in response.data
        assert b'href="/settings/camera"' in response.data


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


def test_dataset_export_endpoint_returns_the_versioned_export():
    exported = {"version": "20260831_220000", "boxes": 2, "directory": "data/datasets/test"}
    exporter = type(
        "Exporter",
        (),
        {"summary": lambda self: {"boxes": 2}, "export": lambda self: exported},
    )()
    training = type("Training", (), {"exporter": exporter})()
    app = create_app(camera=None, status=lambda: {}, training_manager=training)

    response = app.test_client().post("/api/dataset/export")

    assert response.status_code == 201
    assert response.get_json() == {"dataset": exported}


def test_prediction_history_and_model_activation_endpoints_are_available():
    activated = []
    training = type(
        "Training",
        (),
        {"activate": lambda self, version: activated.append(version) or {"version": version}},
    )()
    app = create_app(
        camera=None,
        status=lambda: {},
        training_manager=training,
        prediction_history=lambda: [{"label": "bee"}],
    )
    client = app.test_client()

    assert client.get("/api/predictions").get_json() == [{"label": "bee"}]
    assert client.post("/api/models/20260901_210000/activate").get_json() == {
        "model": {"version": "20260901_210000"}
    }
    assert activated == ["20260901_210000"]


def test_mark_event_empty_endpoint_forwards_only_the_event_id():
    marked = []
    gallery = type(
        "Gallery",
        (),
        {
            "mark_unannotated_frames_empty": lambda self, event_id: (
                marked.append(event_id) or ["frame"]
            )
        },
    )()
    client = create_app(camera=None, status=lambda: {}, gallery=gallery).test_client()

    response = client.post("/api/events/2026-09-01/123000_000001/mark-empty")

    assert response.status_code == 201
    assert response.get_json() == {"frames": ["frame"]}
    assert marked == ["2026-09-01/123000_000001"]


def test_update_endpoints_hide_manager_exception_details():
    class BrokenUpdates:
        def check(self):
            raise RuntimeError("/private/repository/config")

        def install(self):
            raise RuntimeError("token=secret")

    client = create_app(
        camera=None, status=lambda: {}, update_manager=BrokenUpdates()
    ).test_client()

    check = client.post("/updates/check")
    install = client.post("/updates/install")

    assert check.status_code == 503
    assert check.get_json() == {"error": "Update check is temporarily unavailable."}
    assert b"/private/repository/config" not in check.data
    assert install.status_code == 503
    assert install.get_json() == {"error": "Update installation is temporarily unavailable."}
    assert b"token=secret" not in install.data
    app_script = Path(client.application.static_folder) / "app.js"
    assert "!response.ok || result.error" in app_script.read_text(encoding="utf-8")
