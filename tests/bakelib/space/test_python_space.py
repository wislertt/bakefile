import pytest

from bake import Context
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
        assert "pytest" in captured.err
        assert "--cov=src" in captured.err
        assert "--cov-report=html" in captured.err

    def test_setup_dev_runs_uv_sync(self, mock_ctx: Context, capsys: pytest.CaptureFixture) -> None:
        python_space = PythonSpace()
        python_space.setup_dev(mock_ctx)
        captured = capsys.readouterr()
        assert "uv sync" in captured.err
        assert "--all-extras" in captured.err
