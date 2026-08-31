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
