from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_pi_runtime_uses_debian_torch_instead_of_pypi_wheels():
    runtime_script = (PROJECT_ROOT / "scripts" / "sync-pi-runtime.sh").read_text(encoding="utf-8")
    setup_script = (PROJECT_ROOT / "scripts" / "setup-pi.sh").read_text(encoding="utf-8")
    install_script = (PROJECT_ROOT / "scripts" / "install-service.sh").read_text(encoding="utf-8")
    service = (PROJECT_ROOT / "deploy" / "hornet-monitor.service").read_text(encoding="utf-8")

    assert "--system-site-packages --python /usr/bin/python3 .venv" in runtime_script
    assert 'pip uninstall --python "$venv_python" torch torchvision' in runtime_script
    assert "Expected Debian package" in runtime_script
    assert "python3-torch python3-torchvision" in setup_script
    assert "bash scripts/sync-pi-runtime.sh" in install_script
    assert "uv run --no-sync hornet-monitor" in service
