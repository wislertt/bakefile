import sys
from importlib import reload
from pathlib import Path
from unittest.mock import MagicMock, patch

import click
import pytest
import typer

from bake import Context
from bake.cli.common import app as app_module
from bake.cli.common.app import (
    BakefileApp,
    call_app_with_chdir,
    chdir,
    rich_markup_mode,
    show_help_if_no_command,
)
from bake.cli.common.params import validate_file_name, verbosity_callback
from bake.utils.constants import DEFAULT_FILE_NAME


class TestRichMarkupMode:
    def test_rich_markup_mode(self) -> None:
        """rich_markup_mode should be 'rich' or None based on env."""
        # Value depends on env.should_use_colors(), just check it's a valid type
        assert rich_markup_mode in ("rich", None)


class TestShowHelpIfNoCommand:
    def test_show_help_when_no_subcommand(self) -> None:
        """show_help_if_no_command displays help and exits when invoked_subcommand is None."""
        mock_ctx = MagicMock(spec=Context)
        mock_ctx.invoked_subcommand = None
        mock_ctx.get_help.return_value = "Help text"

        with pytest.raises(click.exceptions.Exit):
            show_help_if_no_command(mock_ctx)
        mock_ctx.get_help.assert_called_once()

    def test_no_help_when_subcommand_exists(self) -> None:
        """show_help_if_no_command does nothing when subcommand exists."""
        mock_ctx = MagicMock(spec=Context)
        mock_ctx.invoked_subcommand = "build"

        show_help_if_no_command(mock_ctx)
        mock_ctx.get_help.assert_not_called()


class TestBakefileApp:
    def test_bakefile_app_is_typer(self) -> None:
        """BakefileApp should inherit from typer.Typer."""
        assert issubclass(BakefileApp, typer.Typer)

    def test_bakefile_app_has_bakefile_object_annotation(self) -> None:
        """BakefileApp.bakefile_object should be annotated as BakefileObject."""
        assert hasattr(BakefileApp, "__annotations__")
        assert "bakefile_object" in BakefileApp.__annotations__


class TestValidateFileName:
    def test_validate_file_name_valid(self) -> None:
        """validate_file_name should return valid file names unchanged."""
        result = validate_file_name(DEFAULT_FILE_NAME)
        assert result == DEFAULT_FILE_NAME

    @pytest.mark.parametrize(
        "file_name",
        [f"some/path/{DEFAULT_FILE_NAME}", rf"some\path\{DEFAULT_FILE_NAME}", "bake.txt"],
    )
    def test_validate_file_name_invalid(self, file_name: str) -> None:
        """validate_file_name should raise BadParameter for invalid file names."""
        with pytest.raises(typer.BadParameter):
            validate_file_name(file_name)


class TestVerbosityCallback:
    @pytest.mark.parametrize("value", [0, 1, 2])
    def test_verbosity_callback_valid_values(self, value: int) -> None:
        """verbosity_callback should return valid verbosity values unchanged."""
        mock_ctx = MagicMock()
        mock_param = MagicMock()
        result = verbosity_callback(mock_ctx, mock_param, value)
        assert result == value

    def test_verbosity_callback_raises_for_value_over_2(self) -> None:
        """verbosity_callback should raise BadParameter when value exceeds 2."""
        mock_ctx = MagicMock()
        mock_param = MagicMock()
        with pytest.raises(typer.BadParameter, match="Maximum verbosity is -vv"):
            verbosity_callback(mock_ctx, mock_param, 3)


class TestChdir:
    def test_chdir_changes_and_restores_directory(self, tmp_path: Path) -> None:
        """chdir should change directory and restore original on exit."""
        original = Path.cwd()
        with chdir(tmp_path):
            assert Path.cwd() == tmp_path
        assert Path.cwd() == original

    def test_chdir_restores_on_exception(self, tmp_path: Path) -> None:
        """chdir should restore directory even when exception occurs."""
        original = Path.cwd()
        with pytest.raises(ValueError), chdir(tmp_path):
            assert Path.cwd() == tmp_path
            raise ValueError("test error")
        assert Path.cwd() == original

    def test_custom_chdir_fallback_on_python_310(self, tmp_path: Path) -> None:
        """Custom chdir fallback should work on Python < 3.11."""
        # Mock sys.version_info to simulate Python 3.10
        with patch.object(sys, "version_info", (3, 10, 0)):
            # Reload the module to trigger the conditional import
            reload(app_module)
            from bake.cli.common.app import chdir as custom_chdir

            original = Path.cwd()
            with custom_chdir(tmp_path):
                assert Path.cwd() == tmp_path
            assert Path.cwd() == original

        # Reload again to restore normal behavior
        reload(app_module)


class TestCallAppWithChdir:
    def test_calls_app_without_chdir_when_bakefile_path_is_none(self) -> None:
        """call_app_with_chdir should call app directly when bakefile_path is None."""
        mock_app = MagicMock()

        call_app_with_chdir(mock_app, None, "prog_name", foo="bar")

        mock_app.assert_called_once_with("prog_name", foo="bar")

    def test_calls_app_with_chdir_when_bakefile_path_provided(self, tmp_path: Path) -> None:
        """call_app_with_chdir should change to bakefile parent directory before calling app."""
        mock_app = MagicMock()
        bakefile_path = tmp_path / "bakefile.py"
        bakefile_path.touch()

        original = Path.cwd()
        call_app_with_chdir(mock_app, bakefile_path, "prog_name", foo="bar")

        mock_app.assert_called_once_with("prog_name", foo="bar")
        assert Path.cwd() == original
