import pytest
import typer

from bake import Bakebook, Context
from bakelib.space.base import BaseSpace


def test_base_space_is_bakebook() -> None:
    assert issubclass(BaseSpace, Bakebook)


class TestBaseSpace:
    def test_lint_runs_prettier(self, mock_ctx: Context, capsys: pytest.CaptureFixture) -> None:
        base_space = BaseSpace()
        base_space.lint(mock_ctx)
        captured = capsys.readouterr()
        assert "bunx prettier@latest" in captured.err

    def test_shows_no_implementation_error(self, capsys: pytest.CaptureFixture) -> None:
        base_space = BaseSpace()
        with pytest.raises(typer.Exit):
            base_space.test()
        captured = capsys.readouterr()
        assert "No implementation" in captured.err

    def test_setup_dev_shows_no_implementation_error(self, capsys: pytest.CaptureFixture) -> None:
        base_space = BaseSpace()
        with pytest.raises(typer.Exit):
            base_space.setup_dev()
        captured = capsys.readouterr()
        assert "No implementation" in captured.err

    def test_clean_with_default_excludes(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        base_space = BaseSpace()
        base_space.clean(mock_ctx)
        captured = capsys.readouterr()
        assert "git clean -fdX -n" in captured.err
        assert ".env" in captured.err
        assert ".cache" in captured.err

    def test_clean_with_custom_exclude_patterns(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        base_space = BaseSpace()
        base_space.clean(mock_ctx, exclude_patterns=["*.log", "*.tmp"])
        captured = capsys.readouterr()
        assert "git clean -fdX -n" in captured.err
        assert "*.log" in captured.err or "*.tmp" in captured.err

    def test_clean_with_no_default_excludes(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        base_space = BaseSpace()
        base_space.clean(mock_ctx, use_default_excludes=True)
        captured = capsys.readouterr()
        assert "git clean -fdX -n" in captured.err

    def test_clean_all_runs_git_clean(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        base_space = BaseSpace()
        base_space.clean_all(mock_ctx)
        captured = capsys.readouterr()
        assert "git clean -fdX" in captured.err
