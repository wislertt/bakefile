import sys

import pytest

from bake.utils.constants import CMD_BAKEFILE


def test_bakefile_module_runs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import runpy

    argv = [CMD_BAKEFILE, "--help"]
    monkeypatch.setattr(sys, "argv", argv)

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("bake.cli.bakefile", run_name="__main__")

    assert exc_info.value.code == 0
