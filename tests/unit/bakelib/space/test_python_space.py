from pathlib import Path
from unittest.mock import patch

import pytest
import typer

from bake import Context
from bake.ui.logger import strip_ansi
from bakelib.space.base import BaseSpace
from bakelib.space.python import PythonSpace


def test_python_space_is_base_space() -> None:
    assert issubclass(PythonSpace, BaseSpace)


class TestPythonSpace:
    def test_lint_runs_all_commands(self, mock_ctx: Context, capsys: pytest.CaptureFixture) -> None:
        python_space = PythonSpace()
        python_space.lint(mock_ctx)
        captured = capsys.readouterr()
        assert "toml-sort" in captured.err
        assert "ruff format" in captured.err
        assert "ruff check" in captured.err
        assert "ty check" in captured.err
        assert "deptry" in captured.err

    def test_runs_pytest_with_coverage(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        python_space = PythonSpace()
        python_space.test(mock_ctx)
        captured = capsys.readouterr()
        capture_err = strip_ansi(captured.err)
        assert "pytest" in capture_err
        assert "--cov=src" in capture_err
        assert "--cov-report=html" in capture_err

    def test_setup_dev_runs_uv_sync(self, mock_ctx: Context, capsys: pytest.CaptureFixture) -> None:
        python_space = PythonSpace()
        python_space.setup_dev(mock_ctx)
        captured = capsys.readouterr()
        capture_err = strip_ansi(captured.err)
        assert "uv sync" in capture_err
        assert "--all-extras" in capture_err
        assert "--all-groups" in capture_err
        assert "--frozen" in capture_err

    def test_setup_project_directly_runs_uv_sync(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        python_space = PythonSpace()
        with python_space._set_ctx(mock_ctx):
            python_space.setup_project()
        captured = capsys.readouterr()
        capture_err = strip_ansi(captured.err)
        assert "uv sync" in capture_err
        assert "--all-extras" in capture_err
        assert "--all-groups" in capture_err
        assert "--frozen" in capture_err

    def test_get_python_version_returns_none_when_file_missing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from bakelib.space.python import _get_python_version

        monkeypatch.chdir(tmp_path)
        result = _get_python_version()
        assert result is None

    def test_get_python_version_returns_version_when_file_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from bakelib.space.python import _get_python_version

        python_version_file = tmp_path / ".python-version"
        python_version_file.write_text("3.14\n")
        monkeypatch.chdir(tmp_path)
        result = _get_python_version()
        assert result == "3.14"

    def test_get_tools_includes_python_tool(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        python_version_file = tmp_path / ".python-version"
        python_version_file.write_text("3.14\n")
        monkeypatch.chdir(tmp_path)

        python_space = PythonSpace()
        tools = python_space._get_tools()
        assert "python" in tools
        assert tools["python"].version == "3.14"

    def test_update_runs_lock_upgrade_and_sync(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        python_space = PythonSpace()
        python_space.update(mock_ctx)
        captured = capsys.readouterr()
        capture_err = strip_ansi(captured.err)
        assert "uv lock --upgrade" in capture_err
        assert "uv sync" in capture_err
        assert "--all-extras" in capture_err
        assert "--all-groups" in capture_err

    def test_test_integration_with_verbose_adds_s_v_flags(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        python_space = PythonSpace()
        python_space.test_integration(mock_ctx, verbose=True)
        captured = capsys.readouterr()
        assert "-s -v" in captured.err

    def test_test_integration_without_verbose_no_extra_flags(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        python_space = PythonSpace()
        python_space.test_integration(mock_ctx, verbose=False)
        captured = capsys.readouterr()
        assert "-s -v" not in captured.err

    def test_test_integration_when_dir_doesnt_exist_calls_no_implementation(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        python_space = PythonSpace()
        with patch("bakelib.space.python.Path") as mock_path:
            mock_path.return_value.exists.return_value = False
            with pytest.raises(typer.Exit):
                python_space.test_integration(mock_ctx, verbose=False)
        captured = capsys.readouterr()
        assert "No implementation" in captured.err

    def test_test_all_runs_all_tests_when_unit_tests_exist(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        python_space = PythonSpace()
        with patch("bakelib.space.python.Path") as mock_path:
            mock_path.return_value.exists.return_value = True
            python_space.test_all(mock_ctx)
        captured = capsys.readouterr()
        assert "tests/" in captured.err

    def test_test_all_calls_no_implementation_when_unit_tests_dont_exist(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        python_space = PythonSpace()
        with patch("bakelib.space.python.Path") as mock_path:
            mock_path.return_value.exists.return_value = False
            with pytest.raises(typer.Exit):
                python_space.test_all(mock_ctx)
        captured = capsys.readouterr()
        assert "No implementation" in captured.err
