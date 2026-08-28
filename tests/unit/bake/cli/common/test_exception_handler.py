import errno
from unittest.mock import patch

import pytest

from bake._typer_compat import Abort, ClickException, Exit
from bake.cli.common.exception_handler import typer_exception_handler


def _mock_exit_with_system_exit(code: int = 0) -> None:
    raise SystemExit(code)


class TestTyperExceptionHandlerExceptions:
    @pytest.mark.parametrize(
        ("exc", "expected_code"),
        [
            (EOFError(), 1),
            (KeyboardInterrupt(), 130),
            (Abort(), 1),
            (OSError(errno.EPIPE, "EPIPE"), 1),
        ],
    )
    @patch(
        "bake.cli.common.exception_handler.sys.exit",
        side_effect=_mock_exit_with_system_exit,
    )
    def test_standalone_mode_exits(self, mock_exit, exc, expected_code):
        with (
            pytest.raises(SystemExit),
            typer_exception_handler(standalone_mode=True, rich_markup_mode=None),
        ):
            raise exc
        mock_exit.assert_called_with(expected_code)


class TestTyperExceptionHandlerClickException:
    def test_non_standalone_reraises(self):
        with (
            pytest.raises(ClickException, match="Test error"),
            typer_exception_handler(standalone_mode=False, rich_markup_mode=None),
        ):
            raise ClickException("Test error")

    @pytest.mark.parametrize(
        ("has_rich", "markup_mode"),
        [(False, None), (True, None), (True, "rich")],
    )
    @patch(
        "bake.cli.common.exception_handler.sys.exit",
        side_effect=_mock_exit_with_system_exit,
    )
    def test_standalone_mode_exits_with_code(self, mock_exit, has_rich, markup_mode):
        exc = ClickException("Test error")
        with (
            patch("bake.cli.common.exception_handler.HAS_RICH", has_rich),
            pytest.raises(SystemExit),
            typer_exception_handler(standalone_mode=True, rich_markup_mode=markup_mode),
        ):
            raise exc
        mock_exit.assert_called_with(exc.exit_code)


class TestTyperExceptionHandlerExit:
    @patch(
        "bake.cli.common.exception_handler.sys.exit",
        side_effect=_mock_exit_with_system_exit,
    )
    def test_standalone_exits_with_code(self, mock_exit):
        with (
            pytest.raises(SystemExit),
            typer_exception_handler(standalone_mode=True, rich_markup_mode=None),
        ):
            raise Exit(42)
        mock_exit.assert_called_with(42)

    def test_non_standalone_reraises(self):
        with (
            pytest.raises(Exit) as exc_info,
            typer_exception_handler(standalone_mode=False, rich_markup_mode=None),
        ):
            raise Exit(42)
        assert exc_info.value.exit_code == 42


class TestTyperExceptionHandlerAbort:
    def test_non_standalone_reraises(self):
        with (
            pytest.raises(Abort),
            typer_exception_handler(standalone_mode=False, rich_markup_mode=None),
        ):
            raise Abort()

    @patch(
        "bake.cli.common.exception_handler.sys.exit",
        side_effect=_mock_exit_with_system_exit,
    )
    @pytest.mark.parametrize(("has_rich", "markup_mode"), [(False, None), (True, "rich")])
    def test_standalone_exits(self, _mock_exit, has_rich, markup_mode, capsys):
        with (
            patch("bake.cli.common.exception_handler.HAS_RICH", has_rich),
            pytest.raises(SystemExit),
            typer_exception_handler(standalone_mode=True, rich_markup_mode=markup_mode),
        ):
            raise Abort()
        if not has_rich or markup_mode is None:
            assert "Aborted!" in capsys.readouterr().err


class TestTyperExceptionHandlerOSError:
    def test_non_epipe_reraises(self):
        with (
            pytest.raises(OSError, match="File not found"),
            typer_exception_handler(standalone_mode=True, rich_markup_mode=None),
        ):
            raise OSError(errno.ENOENT, "File not found")

    @patch(
        "bake.cli.common.exception_handler.sys.exit",
        side_effect=_mock_exit_with_system_exit,
    )
    def test_epipe_exits_with_code_1(self, mock_exit):
        with (
            pytest.raises(SystemExit),
            typer_exception_handler(standalone_mode=True, rich_markup_mode=None),
        ):
            raise OSError(errno.EPIPE, "Broken pipe")
        mock_exit.assert_called_with(1)


class TestTyperExceptionHandlerNormalExecution:
    @pytest.mark.parametrize("standalone", [True, False])
    def test_normal_execution(self, standalone):
        result = []
        with typer_exception_handler(standalone_mode=standalone, rich_markup_mode=None):
            result.append("success")
        assert result == ["success"]


class TestTyperExceptionHandlerMarkupModes:
    @pytest.mark.parametrize("markup_mode", ["rich", "markdown", None])
    @patch(
        "bake.cli.common.exception_handler.sys.exit",
        side_effect=_mock_exit_with_system_exit,
    )
    def test_markup_modes_with_rich(self, _mock_exit, markup_mode):
        with (
            patch("bake.cli.common.exception_handler.HAS_RICH", True),
            patch("typer.rich_utils.rich_format_error") as mock_rich,
        ):
            exc = ClickException("Test error")
            with (
                pytest.raises(SystemExit),
                typer_exception_handler(standalone_mode=True, rich_markup_mode=markup_mode),
            ):
                raise exc
            if markup_mode is not None:
                mock_rich.assert_called_once_with(exc)
