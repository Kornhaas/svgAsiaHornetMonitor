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
