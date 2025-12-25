import itertools
import sys
from pathlib import Path

import pytest

from bakefile.cli.bake.main import main


class TestMain:
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
        argv = ["bake", "-C", str(dir_path), *args]
        monkeypatch.setattr(sys, "argv", argv)
        with pytest.raises(SystemExit):
            main()
        captured = capsys.readouterr()
        # All cases should show help with these options
        assert "--chdir" in captured.out and "-C" in captured.out
        assert "--file-name" in captured.out and "-f" in captured.out
        assert "--book-name" in captured.out and "-b" in captured.out

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
        argv = ["bake", "-C", str(dir_path), *args]
        monkeypatch.setattr(sys, "argv", argv)
        with pytest.raises(SystemExit):
            main()
        captured = capsys.readouterr()
        # All cases should show help with these options
        assert "0.0.0" in captured.out
