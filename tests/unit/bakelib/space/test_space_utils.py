import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bake import Context
from bake.ui.logger import strip_ansi
from bakelib.space.utils import (
    check_rust_version_matches_stable,
    orjson_default,
    print_subprocess_output,
)


class TestSetupFunctions:
    def test_setup_brew_runs_brew_commands(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        from bakelib.space.utils import setup_brew

        setup_brew(mock_ctx)
        captured = capsys.readouterr()
        assert "brew update" in captured.err
        assert "brew upgrade" in captured.err
        assert "brew cleanup" in captured.err
        assert "brew list" in captured.err
        assert "brew leaves" in captured.err


class TestOrjsonDefault:
    def test_converts_path_to_string(self) -> None:
        path = Path("/some/path")
        result = orjson_default(path)
        assert result == str(path)

    def test_converts_set_to_list(self) -> None:
        result = orjson_default({1, 2, 3})
        assert isinstance(result, list)
        assert set(result) == {1, 2, 3}

    def test_raises_typeerror_for_unsupported_type(self) -> None:
        with pytest.raises(TypeError):
            orjson_default("unsupported")


class TestCheckRustVersionMatchesStable:
    def test_returns_early_when_versions_match(self, mock_ctx: Context) -> None:
        mock_result = MagicMock()
        mock_result.stdout = "rustc 1.75.0\n"

        with patch.object(mock_ctx, "run", return_value=mock_result):
            check_rust_version_matches_stable(mock_ctx)

    def test_warns_when_versions_differ_with_valid_version_format(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        current_result = MagicMock()
        current_result.stdout = "rustc 1.70.0\n"
        stable_result = MagicMock()
        stable_result.stdout = "rustc 1.75.0\n"

        with patch.object(mock_ctx, "run") as mock_run:
            mock_run.side_effect = [current_result, stable_result]
            check_rust_version_matches_stable(mock_ctx)

        captured = capsys.readouterr()
        output = strip_ansi(captured.err)
        assert "1.70.0" in output
        assert "1.75.0" in output
        assert "differs from stable" in output

    def test_warns_when_versions_differ_with_invalid_version_format(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        current_result = MagicMock()
        current_result.stdout = "rustc custom-build\n"
        stable_result = MagicMock()
        stable_result.stdout = "rustc another-build\n"

        with patch.object(mock_ctx, "run") as mock_run:
            mock_run.side_effect = [current_result, stable_result]
            check_rust_version_matches_stable(mock_ctx)

        captured = capsys.readouterr()
        output = strip_ansi(captured.err)
        assert "custom-build" in output
        assert "another-build" in output
        assert "differs from stable" in output


class TestPrintSubprocessOutput:
    def test_returns_early_when_result_is_none(self, capsys: pytest.CaptureFixture) -> None:
        print_subprocess_output(None)
        captured = capsys.readouterr()
        assert captured.err == ""

    def test_prints_stdout(self, capsys: pytest.CaptureFixture) -> None:
        result = subprocess.CompletedProcess(args=[], returncode=0, stdout="hello world", stderr="")
        print_subprocess_output(result)
        captured = capsys.readouterr()
        assert "stdout:" in captured.err
        assert "hello world" in captured.err

    def test_prints_stderr(self, capsys: pytest.CaptureFixture) -> None:
        result = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="error message"
        )
        print_subprocess_output(result)
        captured = capsys.readouterr()
        assert "stderr:" in captured.err
        assert "error message" in captured.err

    def test_prints_both_stdout_and_stderr(self, capsys: pytest.CaptureFixture) -> None:
        result = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="some output", stderr="some error"
        )
        print_subprocess_output(result)
        captured = capsys.readouterr()
        assert "stdout:" in captured.err
        assert "some output" in captured.err
        assert "stderr:" in captured.err
        assert "some error" in captured.err

    def test_strips_ansi_codes(self, capsys: pytest.CaptureFixture) -> None:
        result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr="\x1b[36mcolored\x1b[0m"
        )
        print_subprocess_output(result)
        captured = capsys.readouterr()
        assert "\x1b[36m" not in captured.err
        assert "colored" in captured.err
