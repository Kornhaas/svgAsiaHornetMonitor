from hornet_monitor.web import create_app


def test_index_and_status_are_available():
    app = create_app(camera=None, status=lambda: {"motion": False, "camera_error": None})
    client = app.test_client()

    index = client.get("/")
    status = client.get("/status")

    assert index.status_code == 200
    assert b"Asia Hornet Monitor" in index.data
    assert status.get_json() == {"camera_error": None, "motion": False}
