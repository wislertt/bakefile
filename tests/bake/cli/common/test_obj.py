from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from bake import Bakebook
from bake.cli.common.app import rich_markup_mode
from bake.cli.common.obj import (
    BakefileObject,
    bakefile_obj_app,
    bakefile_obj_app_args,
    get_bakefile_object,
)
from bake.utils.constants import DEFAULT_BAKEBOOK_NAME, DEFAULT_FILE_NAME


class TestBakefileObject:
    def test_bakefile_object_creation(self) -> None:
        obj = BakefileObject(
            chdir=Path("."),
            file_name=DEFAULT_FILE_NAME,
            bakebook_name=DEFAULT_BAKEBOOK_NAME,
        )
        assert obj.chdir == Path(".")
        assert obj.file_name == DEFAULT_FILE_NAME
        assert obj.bakebook_name == DEFAULT_BAKEBOOK_NAME
        assert obj.bakefile_path is None
        assert obj.bakebook is None

    def test_bakefile_object_get_bakebook_already_loaded(self) -> None:
        obj = BakefileObject(
            chdir=Path("."),
            file_name=DEFAULT_FILE_NAME,
            bakebook_name=DEFAULT_BAKEBOOK_NAME,
        )
        obj.bakebook = Bakebook()
        obj.get_bakebook(allow_missing=False)

    @patch("bake.cli.common.obj.resolve_bakefile_path")
    @patch("bake.cli.common.obj.get_bakebook_from_target_dir_path")
    def test_bakefile_object_get_bakebook_loads_successfully(
        self,
        mock_get_bakebook: MagicMock,
        mock_resolve: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_resolve.return_value = tmp_path / DEFAULT_FILE_NAME
        mock_bakebook = Bakebook()
        mock_get_bakebook.return_value = mock_bakebook

        obj = BakefileObject(
            chdir=tmp_path,
            file_name=DEFAULT_FILE_NAME,
            bakebook_name=DEFAULT_BAKEBOOK_NAME,
        )
        obj.get_bakebook(allow_missing=False)

        assert obj.bakebook is mock_bakebook

    @patch("bake.cli.common.obj.resolve_bakefile_path")
    def test_bakefile_object_get_bakebook_suppresses_errors(
        self, mock_resolve: MagicMock, tmp_path: Path
    ) -> None:
        from bake.utils.exceptions import BakefileNotFoundError

        mock_resolve.side_effect = BakefileNotFoundError("not found")

        obj = BakefileObject(
            chdir=tmp_path,
            file_name=DEFAULT_FILE_NAME,
            bakebook_name=DEFAULT_BAKEBOOK_NAME,
        )
        obj.get_bakebook(allow_missing=False)

        # Should not raise, error suppressed
        assert obj.bakebook is None

    @patch("bake.cli.common.obj.console.warning")
    @patch("bake.cli.common.obj.console.echo")
    def test_bakefile_object_warn_if_no_bakebook(
        self, mock_info: MagicMock, mock_warning: MagicMock
    ) -> None:
        obj = BakefileObject(
            chdir=Path("."),
            file_name=DEFAULT_FILE_NAME,
            bakebook_name=DEFAULT_BAKEBOOK_NAME,
        )
        obj.warn_if_no_bakebook(color_echo=False)

        mock_warning.assert_called_once()
        mock_info.assert_called_once()


class TestBakefileObjAppArgs:
    def test_bakefile_obj_app_args_default(self) -> None:
        # This test uses actual sys.argv; in real tests we'd mock sys.argv
        args = bakefile_obj_app_args()
        assert isinstance(args, list)

    def test_bakefile_obj_app_args_filters_help(self) -> None:
        args = bakefile_obj_app_args(args=["--help", "build"])
        assert "--help" not in args

    def test_bakefile_obj_app_args_filters_version(self) -> None:
        args = bakefile_obj_app_args(args=["--version", "build"])
        assert "--version" not in args


class TestBakefileObjApp:
    def test_bakefile_obj_app_is_typer(self) -> None:
        assert isinstance(bakefile_obj_app, typer.Typer)

    def test_get_bakefile_object_command_registered(self) -> None:
        command_names = [cmd.name for cmd in bakefile_obj_app.registered_commands]
        assert "get_bakefile_object" in command_names


class TestGetBakefileObject:
    @patch("bake.cli.common.obj.bakefile_obj_app_args")
    def test_get_bakefile_object_returns_bakefile_object(self, mock_args: MagicMock) -> None:
        mock_args.return_value = []

        result = get_bakefile_object(rich_markup_mode=rich_markup_mode)
        assert isinstance(result, BakefileObject)
        assert result.chdir == Path(".")
        assert result.file_name == DEFAULT_FILE_NAME
        assert result.bakebook_name == DEFAULT_BAKEBOOK_NAME
        assert result.dry_run is False

    @pytest.mark.parametrize(
        "args,expected_dry_run",
        [([], False), (["--dry-run"], True), (["-n"], True)],
    )
    @patch("bake.cli.common.obj.bakefile_obj_app_args")
    def test_get_bakefile_object_dry_run(
        self, mock_args: MagicMock, args: list[str], expected_dry_run: bool
    ) -> None:
        mock_args.return_value = args

        result = get_bakefile_object(rich_markup_mode=rich_markup_mode)
        assert result.dry_run is expected_dry_run
