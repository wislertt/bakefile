import itertools
from pathlib import Path

import pytest

from bake import __version__
from bake.utils.constants import CMD_BAKEFILE
from tests.conftest import RunCli


class TestMain:
    @pytest.mark.parametrize(
        "dir_fixture,args",
        itertools.product(
            [None, "examples_simple_dir", "examples_no_bakefile_dir"],
            [[], ["--help"]],
        ),
    )
    def test_main_shows_help(
        self,
        dir_fixture: str | None,
        args: list[str],
        request: pytest.FixtureRequest,
        run_cli: RunCli,
    ) -> None:
        dir_path: Path | None = request.getfixturevalue(dir_fixture) if dir_fixture else None
        captured = run_cli(command=CMD_BAKEFILE, dir_path=dir_path, args=args)

        # --help exits with 0 (normal help), no args exits with 1 (error)
        expected_exit_code = 0 if args == ["--help"] else 1
        assert captured.exit_code == expected_exit_code
        assert "--chdir" in captured.out and "-C" in captured.out
        assert "--file-name" in captured.out and "-f" in captured.out
        assert "--book-name" in captured.out and "-b" in captured.out
        assert "--version" in captured.out
        assert "--verbose" in captured.out and "-v" in captured.out
        assert "--chain" in captured.out and "-c" in captured.out
        assert "--dry-run" in captured.out and "-n" in captured.out
        assert "--help" in captured.out

    @pytest.mark.parametrize(
        "dir_fixture,args",
        itertools.product(
            [None, "examples_simple_dir", "examples_no_bakefile_dir"],
            [["--version"]],
        ),
    )
    def test_main_shows_version(
        self,
        dir_fixture: str | None,
        args: list[str],
        request: pytest.FixtureRequest,
        run_cli: RunCli,
    ) -> None:
        dir_path: Path | None = request.getfixturevalue(dir_fixture) if dir_fixture else None
        captured = run_cli(command=CMD_BAKEFILE, dir_path=dir_path, args=args)
        assert captured.exit_code == 0
        assert __version__ in captured.out
