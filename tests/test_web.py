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
