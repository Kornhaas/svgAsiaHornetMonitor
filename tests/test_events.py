from hornet_monitor.events import EventWriter


class _InlineThread:
    def __init__(self, target, args, **_kwargs):
        self.target, self.args = target, args

    def start(self):
        self.target(*self.args)


def test_event_writer_saves_a_burst_and_respects_cooldown(monkeypatch, tmp_path):
    saved = []
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
    monkeypatch.setattr("hornet_monitor.events.time.monotonic", lambda: 100)

    assert writer.save_burst("first")
    assert not writer.save_burst("second")
    assert [frame for _path, frame in saved] == ["first", "next", "next"]
    assert writer.last_event is not None
