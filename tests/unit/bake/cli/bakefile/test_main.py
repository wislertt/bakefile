import itertools
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bake import Context, __version__
from bake.cli.bakefile.main import bakefile_app_callback_with_obj
from bake.cli.common.obj import BakefileObject
from bake.utils.constants import CMD_BAKEFILE, DEFAULT_BAKEBOOK_NAME, DEFAULT_FILE_NAME
from tests.conftest import RunCli


class TestMain:
    @pytest.mark.parametrize(
        "dir_fixture,args",
        list(
            itertools.product(
                [None, "examples_simple_dir", "no_bakefile_dir"],
                [[], ["--help"]],
            )
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
        captured_out = captured.out
        assert captured.exit_code == expected_exit_code
        assert "--chdir" in captured_out and "-C" in captured_out
        assert "--file-name" in captured_out and "-f" in captured_out
        assert "--book-name" in captured_out and "-b" in captured_out
        assert "--version" in captured_out
        assert "--verbose" in captured_out and "-v" in captured_out
        assert "--dry-run" in captured_out and "-n" in captured_out
        assert "--help" in captured_out
        # bakefile CLI does NOT have --chain option (only bake CLI does)

    def test_main_help_contains_agent_docs_pointers(self, run_cli: RunCli) -> None:
        captured = run_cli(command=CMD_BAKEFILE, dir_path=None, args=["--help"])
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
                [None, "examples_simple_dir", "no_bakefile_dir"],
                [["--version"]],
            )
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


class TestBakefileAppCallbackWithObj:
    def test_returns_callable(self) -> None:
        """bakefile_app_callback_with_obj should return a callable."""
        obj = BakefileObject(
            chdir=Path("."),
            file_name=DEFAULT_FILE_NAME,
            bakebook_name=DEFAULT_BAKEBOOK_NAME,
        )
        callback = bakefile_app_callback_with_obj(obj)
        assert callable(callback)

    def test_callback_sets_context_obj(self) -> None:
        """Callback should set obj on context."""
        obj = BakefileObject(
            chdir=Path("."),
            file_name=DEFAULT_FILE_NAME,
            bakebook_name=DEFAULT_BAKEBOOK_NAME,
        )
        callback = bakefile_app_callback_with_obj(obj)

        mock_ctx = MagicMock(spec=Context)
        mock_ctx.invoked_subcommand = "build"

        callback(mock_ctx)
        assert mock_ctx.obj is obj
