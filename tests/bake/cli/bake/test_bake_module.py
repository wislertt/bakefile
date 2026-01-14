import sys
from pathlib import Path

import pytest

from bake.utils.constants import CMD_BAKE


def test_bake_module_runs(
    examples_simple_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import runpy

    argv = [CMD_BAKE, "-C", str(examples_simple_dir), "--help"]
    monkeypatch.setattr(sys, "argv", argv)

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("bake.cli.bake", run_name="__main__")

    assert exc_info.value.code == 0
