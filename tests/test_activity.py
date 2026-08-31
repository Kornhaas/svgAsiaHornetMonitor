from hornet_monitor.activity import ActivityLog


def test_activity_log_persists_and_returns_newest_first(tmp_path):
    log = ActivityLog(tmp_path / "activity.jsonl")
    log.record("started", "Monitor started")
    log.record("motion_event", "Motion event saved")

    entries = log.recent()

    assert [entry["event"] for entry in entries] == ["motion_event", "started"]
