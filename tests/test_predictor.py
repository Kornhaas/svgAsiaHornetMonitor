import json

from hornet_monitor.predictor import _model_path, _model_version


def test_active_model_version_is_returned_only_for_the_active_model(tmp_path):
    models = tmp_path / "models"
    model = models / "20260901_145318" / "weights" / "best.pt"
    model.parent.mkdir(parents=True)
    model.write_bytes(b"model")
    (models / "latest.json").write_text(
        json.dumps({"version": "20260901_145318", "model": str(model)}), encoding="utf-8"
    )

    assert _model_path(models) == model
    assert _model_version(models, model) == "20260901_145318"
    other = models / "other.pt"
    other.write_bytes(b"model")
    assert _model_version(models, other) is None
