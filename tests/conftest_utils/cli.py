import sys
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest

from bake.cli.bake.main import main as bake_main
from bake.cli.bakefile.main import main as bakefile_main
from bake.utils.constants import CMD_BAKE, CMD_BAKEFILE

COMMANDS: dict[str, Callable[[], None]] = {
    CMD_BAKE: bake_main,
    CMD_BAKEFILE: bakefile_main,
}


class CaptureOutput(NamedTuple):
    out: str
    err: str
    exit_code: int


class RunCli:
    def __init__(self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
        self.monkeypatch = monkeypatch
        self.capsys = capsys

    def __call__(self, command: str, dir_path: Path | None, args: list[str]) -> CaptureOutput:
        main_func = COMMANDS[command]
        argv: list[str] = [command, "-C", str(dir_path), *args] if dir_path else [command, *args]
        self.monkeypatch.setattr(sys, "argv", argv)

        with pytest.raises(SystemExit) as exc_info:
            main_func()

        code = exc_info.value.code

        if not isinstance(code, int):
            raise TypeError("Invalid type of exit code")

        captured = self.capsys.readouterr()
        return CaptureOutput(out=captured.out, err=captured.err, exit_code=code)


@pytest.fixture
def run_cli(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> RunCli:
    return RunCli(monkeypatch, capsys)
