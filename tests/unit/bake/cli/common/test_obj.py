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
    is_bakebook_optional,
)
from bake.utils.constants import DEFAULT_BAKEBOOK_NAME, DEFAULT_FILE_NAME
from bake.utils.exceptions import BakebookError


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
    @patch("bake.cli.common.obj.console.error")
    def test_bakefile_object_get_bakebook_not_found_exits_when_allow_missing_false(
        self, mock_error: MagicMock, mock_resolve: MagicMock, tmp_path: Path
    ) -> None:
        from bake.utils.exceptions import BakefileNotFoundError

        mock_resolve.side_effect = BakefileNotFoundError("not found")

        obj = BakefileObject(
            chdir=tmp_path,
            file_name=DEFAULT_FILE_NAME,
            bakebook_name=DEFAULT_BAKEBOOK_NAME,
        )

        with pytest.raises(SystemExit) as exc_info:
            obj.get_bakebook(allow_missing=False)

        assert exc_info.value.code == 1
        mock_error.assert_called_once_with("not found")

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


class TestBakefileObjectResolvePath:
    def test_resolve_bakefile_path_already_set(self, tmp_path: Path) -> None:
        obj = BakefileObject(
            chdir=tmp_path,
            file_name=DEFAULT_FILE_NAME,
            bakebook_name=DEFAULT_BAKEBOOK_NAME,
        )
        pre_set_path = tmp_path / "pre_set.py"
        obj.bakefile_path = pre_set_path

        result = obj.resolve_bakefile_path()
        assert result == pre_set_path

    @patch("bake.cli.common.obj.resolve_bakefile_path")
    def test_resolve_bakefile_path_not_found_returns_none(
        self, mock_resolve: MagicMock, tmp_path: Path
    ) -> None:
        from bake.utils.exceptions import BakefileNotFoundError

        mock_resolve.side_effect = BakefileNotFoundError("not found")

        obj = BakefileObject(
            chdir=tmp_path,
            file_name=DEFAULT_FILE_NAME,
            bakebook_name=DEFAULT_BAKEBOOK_NAME,
        )

        result = obj.resolve_bakefile_path()
        assert result is None


class TestBakefileObjectGetBakebookErrors:
    @patch("bake.cli.common.obj.resolve_bakefile_path")
    @patch("bake.cli.common.obj.get_bakebook_from_target_dir_path")
    @patch("bake.cli.common.obj.console.err.print")
    def test_get_bakebook_validation_error_shows_message(
        self,
        mock_print: MagicMock,
        mock_get_bakebook: MagicMock,
        mock_resolve: MagicMock,
        tmp_path: Path,
    ) -> None:
        from pydantic import ValidationError

        mock_resolve.return_value = tmp_path / DEFAULT_FILE_NAME
        validation_error = ValidationError.from_exception_data("test", [])
        bakebook_error = BakebookError("Invalid")
        bakebook_error.__cause__ = validation_error
        mock_get_bakebook.side_effect = bakebook_error

        obj = BakefileObject(
            chdir=tmp_path,
            file_name=DEFAULT_FILE_NAME,
            bakebook_name=DEFAULT_BAKEBOOK_NAME,
        )

        with pytest.raises(SystemExit) as exc_info:
            obj.get_bakebook(allow_missing=False)

        assert exc_info.value.code == 1
        mock_print.assert_called()

    @patch("bake.cli.common.obj.resolve_bakefile_path")
    @patch("bake.cli.common.obj.get_bakebook_from_target_dir_path")
    @patch("bake.cli.common.obj.console.err.print")
    def test_get_bakebook_generic_error_shows_traceback(
        self,
        mock_print: MagicMock,
        mock_get_bakebook: MagicMock,
        mock_resolve: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_resolve.return_value = tmp_path / DEFAULT_FILE_NAME
        generic_error = ValueError("Something went wrong")
        bakebook_error = BakebookError("Failed")
        bakebook_error.__cause__ = generic_error
        mock_get_bakebook.side_effect = bakebook_error

        obj = BakefileObject(
            chdir=tmp_path,
            file_name=DEFAULT_FILE_NAME,
            bakebook_name=DEFAULT_BAKEBOOK_NAME,
        )

        with pytest.raises(SystemExit) as exc_info:
            obj.get_bakebook(allow_missing=False)

        assert exc_info.value.code == 1
        mock_print.assert_called()

    @patch("bake.cli.common.obj.resolve_bakefile_path")
    def test_get_bakebook_not_found_with_allow_missing_true_returns_early(
        self, mock_resolve: MagicMock, tmp_path: Path
    ) -> None:
        from bake.utils.exceptions import BakefileNotFoundError

        mock_resolve.side_effect = BakefileNotFoundError("not found")

        obj = BakefileObject(
            chdir=tmp_path,
            file_name=DEFAULT_FILE_NAME,
            bakebook_name=DEFAULT_BAKEBOOK_NAME,
        )

        obj.get_bakebook(allow_missing=True)
        assert obj.bakebook is None

    @patch("bake.cli.common.obj.resolve_bakefile_path")
    @patch("bake.cli.common.obj.get_bakebook_from_target_dir_path")
    def test_get_bakebook_with_allow_missing_true_returns_early(
        self, mock_get_bakebook: MagicMock, mock_resolve: MagicMock, tmp_path: Path
    ) -> None:
        mock_resolve.return_value = tmp_path / DEFAULT_FILE_NAME
        mock_get_bakebook.side_effect = BakebookError("Error")

        obj = BakefileObject(
            chdir=tmp_path,
            file_name=DEFAULT_FILE_NAME,
            bakebook_name=DEFAULT_BAKEBOOK_NAME,
        )

        obj.get_bakebook(allow_missing=True)
        assert obj.bakebook is None


class TestGetBakefileObjectErrors:
    @patch("bake.cli.common.obj.bakefile_obj_app_args")
    @patch("bake.cli.common.obj.get_command_from_info")
    def test_get_bakefile_object_wrong_type_raises_type_error(
        self, mock_get_command: MagicMock, mock_args: MagicMock
    ) -> None:
        mock_args.return_value = []
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=MagicMock())
        mock_context.__exit__ = MagicMock(return_value=False)
        mock_command = MagicMock()
        mock_command.make_context.return_value = mock_context
        mock_command.invoke.return_value = "not_a_bakefile_object"
        mock_get_command.return_value = mock_command

        with pytest.raises(TypeError, match=r"Expected.*BakefileObject"):
            get_bakefile_object(rich_markup_mode=rich_markup_mode)

    @patch("bake.cli.common.obj.bakefile_obj_app_args")
    def test_get_bakefile_object_command_not_found_raises_runtime_error(
        self, mock_args: MagicMock
    ) -> None:
        mock_args.return_value = []

        with (
            patch.object(bakefile_obj_app, "registered_commands", []),
            pytest.raises(RuntimeError, match="Failed to find"),
        ):
            get_bakefile_object(rich_markup_mode=rich_markup_mode)


class TestGetBakefileObjectMultipleCommands:
    @patch("bake.cli.common.obj.bakefile_obj_app_args")
    @patch("bake.cli.common.obj.get_command_from_info")
    def test_get_bakefile_object_skips_non_matching_commands(
        self, mock_get_command: MagicMock, mock_args: MagicMock
    ) -> None:
        from bake.cli.common.obj import GET_BAKEFILE_OBJECT

        mock_args.return_value = []

        # Create mock commands - first one doesn't match, second one does
        mock_other_cmd_info = MagicMock()
        mock_other_cmd_info.name = "other_command"

        mock_target_cmd_info = MagicMock()
        mock_target_cmd_info.name = GET_BAKEFILE_OBJECT

        # Setup mock for get_command_from_info - only return valid command for target
        mock_target_command = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=MagicMock())
        mock_context.__exit__ = MagicMock(return_value=False)
        mock_target_command.make_context.return_value = mock_context
        mock_target_command.invoke.return_value = BakefileObject(
            chdir=Path("."),
            file_name=DEFAULT_FILE_NAME,
            bakebook_name=DEFAULT_BAKEBOOK_NAME,
        )

        # When called with other command info, return MagicMock (will be skipped)
        # When called with target command info, return proper mock command
        def side_effect_func(cmd_info, **_kwargs):
            if cmd_info.name == GET_BAKEFILE_OBJECT:
                return mock_target_command
            return MagicMock()

        mock_get_command.side_effect = side_effect_func

        # Mock registered_commands to have multiple commands
        with patch.object(
            bakefile_obj_app, "registered_commands", [mock_other_cmd_info, mock_target_cmd_info]
        ):
            result = get_bakefile_object(rich_markup_mode=rich_markup_mode)
            assert isinstance(result, BakefileObject)


class TestIsBakebookOptional:
    @pytest.mark.parametrize(
        "args,remaining_args,expected",
        [
            (["--help"], None, True),
            (["--version"], None, True),
            (["build"], None, True),
            (["build"], [], True),
            (["build"], ["build"], False),
        ],
    )
    @patch("bake.cli.common.obj.get_args")
    def test_is_bakebook_optional(
        self,
        mock_get_args: MagicMock,
        args: list[str],
        remaining_args: list[str] | None,
        expected: bool,
    ) -> None:
        mock_get_args.return_value = args
        assert is_bakebook_optional(remaining_args=remaining_args) is expected


class TestBakefileObjectSetupLogging:
    @pytest.mark.parametrize("verbosity", [0, 1, 2])
    @patch("bake.cli.common.obj.setup_logging")
    def test_setup_logging(self, mock_setup_logging: MagicMock, verbosity: int) -> None:
        obj = BakefileObject(
            chdir=Path("."),
            file_name=DEFAULT_FILE_NAME,
            bakebook_name=DEFAULT_BAKEBOOK_NAME,
            verbosity=verbosity,
        )
        obj.setup_logging()
        mock_setup_logging.assert_called_once()


class TestBakefileObjectIsStandalone:
    def test_is_standalone_bakefile_returns_false_when_path_is_none(self) -> None:
        obj = BakefileObject(
            chdir=Path("."),
            file_name=DEFAULT_FILE_NAME,
            bakebook_name=DEFAULT_BAKEBOOK_NAME,
        )
        assert obj.is_standalone_bakefile is False

    @patch("bake.cli.common.obj.is_standalone_bakefile")
    def test_is_standalone_bakefile_returns_true_for_standalone(
        self, mock_is_standalone: MagicMock, tmp_path: Path
    ) -> None:
        mock_is_standalone.return_value = True
        bakefile_path = tmp_path / DEFAULT_FILE_NAME

        obj = BakefileObject(
            chdir=tmp_path,
            file_name=DEFAULT_FILE_NAME,
            bakebook_name=DEFAULT_BAKEBOOK_NAME,
            bakefile_path=bakefile_path,
        )

        assert obj.is_standalone_bakefile is True
        mock_is_standalone.assert_called_once_with(bakefile_path)

    @patch("bake.cli.common.obj.is_standalone_bakefile")
    def test_is_standalone_bakefile_returns_false_for_non_standalone(
        self, mock_is_standalone: MagicMock, tmp_path: Path
    ) -> None:
        mock_is_standalone.return_value = False
        bakefile_path = tmp_path / DEFAULT_FILE_NAME

        obj = BakefileObject(
            chdir=tmp_path,
            file_name=DEFAULT_FILE_NAME,
            bakebook_name=DEFAULT_BAKEBOOK_NAME,
            bakefile_path=bakefile_path,
        )

        assert obj.is_standalone_bakefile is False
        mock_is_standalone.assert_called_once_with(bakefile_path)
