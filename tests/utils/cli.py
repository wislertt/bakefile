import sys
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest

from bake.cli.bake.main import main as bake_main
from bake.cli.bakefile.main import main as bakefile_main
from bake.ui.logger import strip_ansi
from bake.utils.constants import CMD_BAKE, CMD_BAKEFILE
from bake.utils.settings import bake_settings

COMMANDS: dict[str, Callable[[], None]] = {
    CMD_BAKE: bake_main,
    CMD_BAKEFILE: bakefile_main,
}


class CaptureOutput(NamedTuple):
    out: str
    err: str
    exit_code: int

    def stripped(self) -> "CaptureOutput":
        """Return a new CaptureOutput with ANSI codes stripped from out and err."""
        return CaptureOutput(
            out=strip_ansi(self.out),
            err=strip_ansi(self.err),
            exit_code=self.exit_code,
        )


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
        return CaptureOutput(out=captured.out, err=captured.err, exit_code=code).stripped()


@pytest.fixture
def run_cli(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> RunCli:
    return RunCli(monkeypatch, capsys)


def get_error_label(github_actions: bool | None = None) -> str:
    """Get the error label based on current environment or provided value."""
    if github_actions is None:
        github_actions = bake_settings.github_actions
    return "ERROR" if not github_actions else "::error::"


def get_warning_label(github_actions: bool | None = None) -> str:
    """Get the warning label based on current environment or provided value."""
    if github_actions is None:
        github_actions = bake_settings.github_actions
    return "WARNING" if not github_actions else "::warning::"
