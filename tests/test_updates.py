from hornet_monitor.updates import UpdateManager


class ActivityLogStub:
    def record(self, *_args, **_kwargs):
        pass


def test_disabled_web_updates_do_not_run_commands(tmp_path):
    manager = UpdateManager({"enabled": False, "repository": str(tmp_path)}, ActivityLogStub())

    assert manager.check()["state"] == "disabled"
    assert manager.install()["state"] == "disabled"
