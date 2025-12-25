import itertools
import sys
from pathlib import Path
from typing import NamedTuple

import pytest

from bakefile import __version__
from bakefile.cli.bake.main import main


class CaptureOutput(NamedTuple):
    out: str
    err: str
    exit_code: int


class TestMain:
    def _run_main_with_args(
        self,
        dir_path: Path,
        args: list[str],
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> CaptureOutput:
        argv = ["bake", "-C", str(dir_path), *args]
        monkeypatch.setattr(sys, "argv", argv)

        with pytest.raises(SystemExit) as exc_info:
            main()

        code = exc_info.value.code

        if not isinstance(code, int):
            raise TypeError("Invalid type of exit code")

        captured = capsys.readouterr()
        return CaptureOutput(out=captured.out, err=captured.err, exit_code=code)

    @pytest.mark.parametrize(
        "dir_fixture,args",
        itertools.product(
            ["examples_simple_dir", "examples_no_bakebook_dir", "examples_no_bakefile_dir"],
            [[], ["--help"]],
        ),
    )
    def test_main_shows_help(
        self,
        dir_fixture: str,
        args: list[str],
        request: pytest.FixtureRequest,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        dir_path: Path = request.getfixturevalue(dir_fixture)
        captured = self._run_main_with_args(dir_path, args, monkeypatch, capsys)

        assert captured.exit_code == 0
        # All cases should show help with these options
        assert "--chdir" in captured.out and "-C" in captured.out
        assert "--file-name" in captured.out and "-f" in captured.out
        assert "--book-name" in captured.out and "-b" in captured.out
        assert "--version" in captured.out
        assert "--help" in captured.out

        if dir_fixture == "examples_simple_dir":
            assert "hello" in captured.out
        else:
            assert "hello" not in captured.out

    @pytest.mark.parametrize(
        "dir_fixture,args",
        itertools.product(
            ["examples_simple_dir", "examples_no_bakebook_dir", "examples_no_bakefile_dir"],
            [["--version"]],
        ),
    )
    def test_main_shows_version(
        self,
        dir_fixture: str,
        args: list[str],
        request: pytest.FixtureRequest,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        dir_path: Path = request.getfixturevalue(dir_fixture)
        captured = self._run_main_with_args(dir_path, args, monkeypatch, capsys)
        assert captured.exit_code == 0
        assert __version__ in captured.out

    def test_main_hello_command(
        self,
        examples_simple_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        captured = self._run_main_with_args(examples_simple_dir, ["hello"], monkeypatch, capsys)
        assert captured.exit_code == 0
        assert captured.out == "Hello world!\n"

    def test_main_hello_command_no_bakefile_dir(
        self,
        examples_no_bakefile_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        captured = self._run_main_with_args(
            examples_no_bakefile_dir, ["hello"], monkeypatch, capsys
        )
        assert captured.exit_code == 2
        assert "File not found" in captured.err
        # assert "No such command 'hello'." not in captured.err
