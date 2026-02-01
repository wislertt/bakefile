from unittest.mock import MagicMock

import click
import pytest
import typer

from bake import Context
from bake.cli.common.app import (
    BakefileApp,
    rich_markup_mode,
    show_help_if_no_command,
)
from bake.cli.common.params import validate_file_name
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
