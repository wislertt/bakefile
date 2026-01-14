import itertools
from pathlib import Path

import pytest

from bake import __version__
from bake.ui.logger import strip_ansi
from bake.utils.constants import CMD_BAKE
from tests.conftest import RunCli


class TestMain:
    @pytest.mark.parametrize(
        "dir_fixture, args",
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
        run_cli: RunCli,
    ) -> None:
        dir_path: Path = request.getfixturevalue(dir_fixture)
        captured = run_cli(command=CMD_BAKE, dir_path=dir_path, args=args)

        expected_exit_code = 0 if args == ["--help"] else 1
        assert captured.exit_code == expected_exit_code
        # All cases should show help with these options
        captured_out = strip_ansi(captured.out)
        assert "--chdir" in captured_out and "-C" in captured_out
        assert "--file-name" in captured_out and "-f" in captured_out
        assert "--book-name" in captured_out and "-b" in captured_out
        assert "--version" in captured_out
        assert "--verbose" in captured_out and "-v" in captured_out
        assert "--chain" in captured_out and "-c" in captured_out
        assert "--dry-run" in captured_out and "-n" in captured_out
        assert "--help" in captured_out

        if dir_fixture == "examples_simple_dir":
            assert "hello" in captured_out
        else:
            assert "hello" not in captured_out

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
        examples_no_bakefile_dir: Path,
        run_cli: RunCli,
    ) -> None:
        captured = run_cli(command=CMD_BAKE, dir_path=examples_no_bakefile_dir, args=["hello"])
        assert captured.exit_code == 2
        # New warning format from warn_if_no_bakebook
        assert "Bakebook" in captured.err and "not found" in captured.err

    def test_main_dry_run(
        self,
        examples_simple_dir: Path,
        run_cli: RunCli,
    ) -> None:
        captured = run_cli(
            command=CMD_BAKE, dir_path=examples_simple_dir, args=["--dry-run", "build"]
        )
        assert captured.exit_code == 0
        assert "This is dry run" in captured.err

    def test_main_chain_commands_success(
        self,
        examples_simple_dir: Path,
        run_cli: RunCli,
    ) -> None:
        captured = run_cli(
            command=CMD_BAKE,
            dir_path=examples_simple_dir,
            args=["--dry-run", "--chain", "hello", "build"],
        )
        assert captured.exit_code == 0

        captured_out = strip_ansi(captured.out)
        assert "Hello world!" in captured_out
        assert "Building..." in captured_out

    def test_main_chain_commands_failure_stops_execution(
        self,
        examples_simple_dir: Path,
        run_cli: RunCli,
    ) -> None:
        captured = run_cli(
            command=CMD_BAKE,
            dir_path=examples_simple_dir,
            args=["--dry-run", "--chain", "hello", "nonexistent", "build"],
        )
        assert captured.exit_code != 0
        assert "Hello world!" in captured.out
        # build should not run after nonexistent fails
        assert "Building..." not in captured.out
