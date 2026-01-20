import itertools
from pathlib import Path

import pytest

from bake import __version__
from bake.utils.constants import CMD_BAKE
from tests.conftest import RunCli


class TestMain:
    @pytest.mark.parametrize(
        "dir_fixture, args",
        itertools.product(
            ["examples_simple_dir", "no_bakebook_dir", "no_bakefile_dir"],
            [[], ["--help"]],
        ),
    )
    def test_main_shows_help(
        self,
        dir_fixture: str,
        args: list[str],
        request: pytest.FixtureRequest,
        run_cli: RunCli,
    ) -> None:
        dir_path: Path = request.getfixturevalue(dir_fixture)
        captured = run_cli(command=CMD_BAKE, dir_path=dir_path, args=args)

        expected_exit_code = 0 if args == ["--help"] else 1
        assert captured.exit_code == expected_exit_code
        # All cases should show help with these options
        assert "--chdir" in captured.out and "-C" in captured.out
        assert "--file-name" in captured.out and "-f" in captured.out
        assert "--book-name" in captured.out and "-b" in captured.out
        assert "--version" in captured.out
        assert "--verbose" in captured.out and "-v" in captured.out
        assert "--chain" in captured.out and "-c" in captured.out
        assert "--dry-run" in captured.out and "-n" in captured.out
        assert "--help" in captured.out

        if dir_fixture == "examples_simple_dir":
            assert "hello" in captured.out
        else:
            assert "hello" not in captured.out

    @pytest.mark.parametrize(
        "dir_fixture,args",
        itertools.product(
            ["examples_simple_dir", "no_bakebook_dir", "no_bakefile_dir"],
            [["--version"]],
        ),
    )
    def test_main_shows_version(
        self,
        dir_fixture: str,
        args: list[str],
        request: pytest.FixtureRequest,
        run_cli: RunCli,
    ) -> None:
        dir_path: Path = request.getfixturevalue(dir_fixture)
        captured = run_cli(command=CMD_BAKE, dir_path=dir_path, args=args)
        assert captured.exit_code == 0
        assert __version__ in captured.out

    def test_main_hello_command(
        self,
        examples_simple_dir: Path,
        run_cli: RunCli,
    ) -> None:
        captured = run_cli(command=CMD_BAKE, dir_path=examples_simple_dir, args=["hello"])
        assert captured.exit_code == 0
        assert captured.out == "Hello world!\n"

    def test_main_hello_command_no_bakefile_dir(
        self,
        no_bakefile_dir: Path,
        run_cli: RunCli,
    ) -> None:
        captured = run_cli(command=CMD_BAKE, dir_path=no_bakefile_dir, args=["hello"])
        assert captured.exit_code == 1
        # New warning format from warn_if_no_bakebook
        assert "Directory not found:" in captured.err

    def test_main_chain_commands_success(
        self,
        examples_simple_dir: Path,
        run_cli: RunCli,
    ) -> None:
        captured = run_cli(
            command=CMD_BAKE,
            dir_path=examples_simple_dir,
            args=["--chain", "hello", "foo"],
        )
        assert captured.exit_code == 0

        assert "Hello world!" in captured.out
        assert "Doing foo with" in captured.out

    def test_main_chain_commands_failure_stops_execution(
        self,
        examples_simple_dir: Path,
        run_cli: RunCli,
    ) -> None:
        captured = run_cli(
            command=CMD_BAKE,
            dir_path=examples_simple_dir,
            args=["--chain", "hello", "nonexistent", "foo"],
        )
        assert captured.exit_code != 0
        assert "Hello world!" in captured.out
        # foo should not run after nonexistent fails
        assert "Doing foo with" not in captured.out
