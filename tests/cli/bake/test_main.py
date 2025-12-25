import itertools
import sys
from pathlib import Path

import pytest

from bakefile import __version__
from bakefile.cli.bake.main import main


class TestMain:
    def _run_main_with_args(
        self,
        dir_path: Path,
        args: list[str],
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ):
        argv = ["bake", "-C", str(dir_path), *args]
        monkeypatch.setattr(sys, "argv", argv)
        with pytest.raises(SystemExit):
            main()
        return capsys.readouterr()

    @pytest.mark.parametrize(
        "dir_fixture,args",
        itertools.product(
            ["examples_simple_dir", "examples_no_bakebook_dir", "examples_no_bakefile_dir"],
            [[], ["--help"]],
        ),
    )
    def test_main_shows_help_with_options(
        self,
        dir_fixture: str,
        args: list[str],
        request: pytest.FixtureRequest,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        dir_path: Path = request.getfixturevalue(dir_fixture)
        captured = self._run_main_with_args(dir_path, args, monkeypatch, capsys)
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
        assert __version__ in captured.out
