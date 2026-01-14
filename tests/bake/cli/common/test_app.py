from pathlib import Path
from unittest.mock import MagicMock

import click
import pytest
import typer

from bake import Context
from bake.cli.common.app import (
    BakefileApp,
    bake_app_callback_with_obj,
    rich_markup_mode,
    show_help_if_no_command,
)
from bake.cli.common.obj import BakefileObject
from bake.utils.constants import DEFAULT_BAKEBOOK_NAME, DEFAULT_FILE_NAME


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
