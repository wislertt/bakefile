import itertools
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bake import Context, __version__
from bake.cli.bake.main import bake_app_callback_with_obj
from bake.cli.common.obj import BakefileObject
from bake.utils.constants import CMD_BAKE, DEFAULT_BAKEBOOK_NAME, DEFAULT_FILE_NAME
from tests.conftest import RunCli


class TestMain:
    @pytest.mark.parametrize(
        "dir_fixture, args",
        list(
            itertools.product(
                ["examples_simple_dir", "no_bakebook_dir", "no_bakefile_dir"],
                [[], ["--help"]],
            )
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

    def test_main_help_contains_agent_docs_pointers(
        self,
        examples_simple_dir: Path,
        run_cli: RunCli,
    ) -> None:
        captured = run_cli(command=CMD_BAKE, dir_path=examples_simple_dir, args=["--help"])
        assert "Docs: https://bakefile.wisl.dev" in captured.out
        assert (
            "Full docs in one file (for AI agents): https://bakefile.wisl.dev/llms-full.txt"
            in captured.out
        )
        assert "Docs index: https://bakefile.wisl.dev/llms.txt" in captured.out
        assert "Agent skill: https://bakefile.wisl.dev/skill.md" in captured.out
        assert "Install agent skill: `npx skills add https://bakefile.wisl.dev`" in captured.out
        assert "Docs search via MCP: https://bakefile.wisl.dev/mcp" in captured.out

    @pytest.mark.parametrize(
        "dir_fixture,args",
        list(
            itertools.product(
                ["examples_simple_dir", "no_bakebook_dir", "no_bakefile_dir"],
                [["--version"]],
            )
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

    def test_main_cwd_command(
        self,
        examples_simple_dir: Path,
        run_cli: RunCli,
    ) -> None:
        captured = run_cli(command=CMD_BAKE, dir_path=examples_simple_dir, args=["cwd"])
        assert captured.exit_code == 0
        assert str(examples_simple_dir) == captured.out.strip()

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


class TestBakeAppCallbackWithObj:
    def test_returns_callable(self) -> None:
        """bake_app_callback_with_obj should return a callable."""
        obj = BakefileObject(
            chdir=Path("."),
            file_name=DEFAULT_FILE_NAME,
            bakebook_name=DEFAULT_BAKEBOOK_NAME,
        )
        callback = bake_app_callback_with_obj(obj)
        assert callable(callback)

    def test_callback_sets_context_obj(self) -> None:
        """Callback should set obj on context."""
        obj = BakefileObject(
            chdir=Path("."),
            file_name=DEFAULT_FILE_NAME,
            bakebook_name=DEFAULT_BAKEBOOK_NAME,
        )
        callback = bake_app_callback_with_obj(obj)

        mock_ctx = MagicMock(spec=Context)
        mock_ctx.invoked_subcommand = "build"

        callback(mock_ctx)
        assert mock_ctx.obj is obj
