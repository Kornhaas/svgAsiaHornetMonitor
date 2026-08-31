import importlib.util
from pathlib import Path


def load_training_module():
    path = Path(__file__).parents[1] / "training" / "train_local.py"
    specification = importlib.util.spec_from_file_location("train_local", path)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def test_find_dataset_uses_the_most_recent_versioned_export(tmp_path):
    old = tmp_path / "20260901_210000" / "dataset.yaml"
    latest = tmp_path / "20260901_220000" / "dataset.yaml"
    old.parent.mkdir()
    latest.parent.mkdir()
    old.write_text("names: []", encoding="utf-8")
    latest.write_text("names: []", encoding="utf-8")

    assert load_training_module().find_dataset(tmp_path) == latest


def test_training_scripts_resolve_the_repository_root():
    assert (load_training_module().repository_root() / "pyproject.toml").is_file()
