from hornet_monitor.camera import Camera


class _Capture:
    def __init__(self, opened):
        self.opened = opened

    def set(self, *_args):
        pass

    def isOpened(self):
        return self.opened

    def release(self):
        pass


def test_camera_starts_reader_even_when_initial_open_fails(monkeypatch):
    calls = []

    def open_camera(*_args):
        calls.append(True)
        return _Capture(False)

    monkeypatch.setattr("hornet_monitor.camera.cv2.VideoCapture", open_camera)
    camera = Camera(
        {
            "device": "/dev/video0",
            "width": 1,
            "height": 1,
            "fps": 1,
            "reconnect_seconds": 60,
        }
    )

    camera.start()
    try:
        assert camera._thread is not None
        assert camera._thread.is_alive()
        assert calls
    finally:
        camera.stop()


def test_camera_opens_and_resets_its_retry_delay(monkeypatch):
    capture = _Capture(True)
    monkeypatch.setattr("hornet_monitor.camera.cv2.VideoCapture", lambda *_args: capture)
    camera = Camera(
        {"device": "/dev/video0", "width": 1, "height": 1, "fps": 1, "reconnect_seconds": 5}
    )
    camera._retry_seconds = 40

    assert camera._open()
    assert camera._capture is capture
    assert camera._retry_seconds == 5
