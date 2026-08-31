from datetime import datetime, timedelta
from zipfile import ZipFile

from hornet_monitor.storage import StorageManager


def test_storage_backup_contains_local_metadata(tmp_path):
    annotations = tmp_path / "annotations.jsonl"
    annotations.write_text("{}\n", encoding="utf-8")
    storage = StorageManager(
        {
            "directory": str(tmp_path),
            "backup_directory": str(tmp_path / "backups"),
            "minimum_free_gb": 1,
        },
        [str(annotations)],
    )

    archive = storage.backup()

    assert archive.endswith(".zip")
    assert storage.status()["free_gb"] >= 0


def test_storage_backup_includes_nested_event_and_model_files_and_cleanup(tmp_path):
    events = tmp_path / "events"
    old_event = events / "2026-08-01" / "old" / "frame_000.jpg"
    reviewed_event = events / "2026-08-01" / "reviewed" / "frame_000.jpg"
    model = tmp_path / "models" / "version" / "weights" / "best.pt"
    for file in (old_event, reviewed_event, model):
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(b"data")
    old = (datetime.now() - timedelta(days=10)).timestamp()
    import os

    os.utime(old_event.parent, (old, old))
    os.utime(reviewed_event.parent, (old, old))
    annotations = tmp_path / "annotations.jsonl"
    annotations.write_text('{"image":"2026-08-01/reviewed/frame_000.jpg"}\n', encoding="utf-8")
    storage = StorageManager(
        {
            "directory": str(tmp_path),
            "backup_directory": str(tmp_path / "backups"),
            "minimum_free_gb": 1,
            "reviewed_retention_days": 30,
            "unreviewed_retention_days": 7,
        },
        [str(events), str(model.parents[2])],
        str(events),
        str(annotations),
    )

    archive = storage.backup()
    result = storage.cleanup()

    with ZipFile(archive) as backup:
        assert "events/2026-08-01/old/frame_000.jpg" in backup.namelist()
        assert "models/version/weights/best.pt" in backup.namelist()
    assert result["deleted"] == 1
    assert not old_event.parent.exists()
    assert reviewed_event.parent.exists()
