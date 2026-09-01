from pathlib import Path

import hornet_monitor.updates as updates_module
from hornet_monitor.updates import UpdateManager


class ActivityLogStub:
    def record(self, *_args, **_kwargs):
        pass


def test_disabled_web_updates_do_not_run_commands(tmp_path):
    manager = UpdateManager({"enabled": False, "repository": str(tmp_path)}, ActivityLogStub())

    assert manager.check()["state"] == "disabled"
    assert manager.install()["state"] == "disabled"


def test_update_check_does_not_return_subprocess_details(tmp_path):
    manager = UpdateManager({"enabled": True, "repository": str(tmp_path)}, ActivityLogStub())
    manager._git = lambda *_arguments: (_ for _ in ()).throw(OSError("/private/repository/config"))

    assert manager.check() == {"state": "error", "message": "Update check failed."}
    assert manager._state == {"state": "error", "message": "Update check failed."}


def test_update_check_hides_malformed_git_output(tmp_path):
    manager = UpdateManager({"enabled": True, "repository": str(tmp_path)}, ActivityLogStub())
    answers = iter(("", "abcd123", "not-a-number"))
    manager._git = lambda *_arguments: next(answers)

    assert manager.check() == {"state": "error", "message": "Update check failed."}


def test_install_runs_fixed_pi_runtime_sync_script(tmp_path, monkeypatch):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    runtime_script = scripts / "sync-pi-runtime.sh"
    runtime_script.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    calls: list[tuple[list[str], Path]] = []

    def run(arguments, *, cwd, check):
        calls.append((arguments, cwd))

    monkeypatch.setattr(updates_module.subprocess, "run", run)
    monkeypatch.setattr(updates_module.subprocess, "Popen", lambda *_args: None)
    manager = UpdateManager(
        {"enabled": True, "repository": str(tmp_path), "service": "hornet-monitor.service"},
        ActivityLogStub(),
    )

    manager._install()

    assert calls == [
        (["git", "pull", "--ff-only"], tmp_path),
        (["bash", str(runtime_script.resolve())], tmp_path),
    ]
    assert manager._state["state"] == "restarting"
