from pathlib import Path


def test_reset_script_requires_confirmation_and_limits_deletion_targets():
    script = (Path(__file__).parents[1] / "scripts" / "reset-runtime-data.sh").read_text(
        encoding="utf-8"
    )

    assert "--yes" in script
    assert '"$data_dir/events"' in script
    assert '"$data_dir/annotations.jsonl"' in script
    assert '"$data_dir/models"' in script
    assert '"$data_dir/backups"' in script
    assert '"$data_dir"/*) rm -rf -- "$target"' in script
