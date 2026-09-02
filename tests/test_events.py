from hornet_monitor.events import EventWriter


class _InlineThread:
    def __init__(self, target, args, **_kwargs):
        self.target, self.args = target, args

    def start(self):
        self.target(*self.args)


def test_event_writer_saves_a_burst_and_respects_cooldown(monkeypatch, tmp_path):
    saved = []
    completed = []
    monkeypatch.setattr(
        "hornet_monitor.events.cv2.imwrite", lambda path, frame: saved.append((path, frame))
    )
    monkeypatch.setattr("hornet_monitor.events.threading.Thread", _InlineThread)
    monkeypatch.setattr("hornet_monitor.events.time.sleep", lambda _seconds: None)
    writer = EventWriter(
        {
            "directory": str(tmp_path),
            "cooldown_seconds": 60,
            "burst_frames": 3,
            "burst_interval_seconds": 0,
        }
    )
    writer.frame_supplier = lambda: "next"
    writer.burst_complete_callback = lambda folder: completed.append(folder)
    monkeypatch.setattr("hornet_monitor.events.time.monotonic", lambda: 100)

    assert writer.save_burst("first")
    assert not writer.save_burst("second")
    assert [frame for _path, frame in saved] == ["first", "next", "next"]
    assert writer.last_event is not None
    assert len(completed) == 1
    assert str(completed[0]) == writer.last_event


def test_event_writer_marks_dark_preview_metadata():
    import numpy as np

    assert EventWriter._brightness(np.zeros((2, 2, 3), dtype=np.uint8)) == 0.0


def test_event_writer_records_a_manual_capture(monkeypatch, tmp_path):
    entries = []
    monkeypatch.setattr("hornet_monitor.events.cv2.imwrite", lambda *_args: True)
    monkeypatch.setattr("hornet_monitor.events.threading.Thread", _InlineThread)
    monkeypatch.setattr("hornet_monitor.events.time.sleep", lambda _seconds: None)
    writer = EventWriter(
        {"directory": str(tmp_path), "cooldown_seconds": 1, "burst_frames": 1},
        activity_log=type(
            "Log", (), {"record": lambda _self, *args, **kwargs: entries.append(args)}
        )(),
    )

    assert writer.save_burst("frame", event="manual_event")
    assert entries[0][:2] == ("manual_event", "Manual event saved")
