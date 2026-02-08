import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from bake import Bakebook, Context
from bake.ui.logger import strip_ansi
from bakelib.space.base import BaseSpace, ToolInfo


def test_base_space_is_bakebook() -> None:
    assert issubclass(BaseSpace, Bakebook)


class TestBaseSpace:
    def test_lint_runs_prettier(self, mock_ctx: Context, capsys: pytest.CaptureFixture) -> None:
        base_space = BaseSpace()
        with mock_ctx:
            base_space.lint()
        captured = capsys.readouterr()
        assert "bunx prettier@latest" in captured.err

    def test_shows_no_implementation_error(self, capsys: pytest.CaptureFixture) -> None:
        base_space = BaseSpace()
        with pytest.raises(typer.Exit):
            base_space.test()
        captured = capsys.readouterr()
        assert "No implementation" in captured.err

    def test_setup_dev_shows_no_implementation_error(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        base_space = BaseSpace()
        with mock_ctx:
            base_space.setup_dev()
        captured = capsys.readouterr()
        assert "brew install uv" in captured.err

    def test_clean_with_default_excludes(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        base_space = BaseSpace()
        with mock_ctx:
            base_space.clean()
        captured = capsys.readouterr()
        assert "git clean -fdX -n" in captured.err
        assert ".env" in captured.err
        assert ".cache" in captured.err

    def test_clean_with_custom_exclude_patterns(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        base_space = BaseSpace()
        with mock_ctx:
            base_space.clean(exclude_patterns=["*.log", "*.tmp"])
        captured = capsys.readouterr()
        assert "git clean -fdX -n" in captured.err
        assert "*.log" in captured.err or "*.tmp" in captured.err

    def test_clean_with_no_default_excludes(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        base_space = BaseSpace()
        with mock_ctx:
            base_space.clean(default_excludes=False)
        captured = capsys.readouterr()
        assert "git clean -fdX -n" in captured.err

    def test_clean_all_runs_git_clean(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        base_space = BaseSpace()
        with mock_ctx:
            base_space.clean_all()
        captured = capsys.readouterr()
        assert "git clean -fdX" in captured.err

    def test_tools_outputs_json_by_default(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        base_space = BaseSpace()
        with mock_ctx:
            base_space.tools()
        captured = capsys.readouterr()
        output = json.loads(strip_ansi(captured.out))
        assert isinstance(output, dict)
        assert "bun" in output
        assert "uv" in output

    def test_tools_outputs_names_format(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        base_space = BaseSpace()
        with mock_ctx:
            base_space.tools(format="names")
        captured = capsys.readouterr()
        names = captured.out.strip().split("\n")
        assert "bun" in names
        assert "uv" in names
        assert "bakefile" in names

    def test_assert_which_path_returns_true_in_dry_run(self, mock_ctx: Context) -> None:
        base_space = BaseSpace()
        mock_ctx.dry_run = True
        tool_info = ToolInfo(expected_paths=[])
        with mock_ctx:
            result = base_space._assert_which_path("test", tool_info)
        assert result is True

    def test_assert_which_path_returns_true_when_path_matches(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        base_space = BaseSpace()
        mock_ctx.dry_run = False

        expected_path = Path("/usr/bin/test")
        tool_info = ToolInfo(expected_paths=[expected_path])

        # Mock the run method to return the expected path
        mock_result = MagicMock()
        mock_result.stdout = str(expected_path) + "\n"

        with patch.object(mock_ctx, "run", return_value=mock_result):
            with mock_ctx:
                result = base_space._assert_which_path("test", tool_info)
            assert result is True

            captured = capsys.readouterr()
            output = strip_ansi(captured.out)
            assert "test:" in output
            assert str(expected_path) in output

    def test_assert_which_path_returns_false_when_path_mismatch(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        base_space = BaseSpace()
        mock_ctx.dry_run = False

        expected_path = Path("/usr/bin/test")
        actual_path = Path("/usr/local/bin/test")
        tool_info = ToolInfo(expected_paths=[expected_path])

        # Mock the run method to return a different path
        mock_result = MagicMock()
        mock_result.stdout = str(actual_path) + "\n"

        with patch.object(mock_ctx, "run", return_value=mock_result):
            with mock_ctx:
                result = base_space._assert_which_path("test", tool_info)
            assert result is False

            captured = capsys.readouterr()
            output = strip_ansi(captured.err)
            assert "unexpected location" in output
            assert str(actual_path) in output

    def test_get_tools_returns_tool_info_dict(self) -> None:
        base_space = BaseSpace()
        tools = base_space._get_tools()
        assert isinstance(tools, dict)
        assert "bun" in tools
        assert "uv" in tools
        assert isinstance(tools["bun"], ToolInfo)

    def test_assert_setup_dev_runs_lint_and_test(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        base_space = BaseSpace()
        mock_ctx.dry_run = True
        with mock_ctx, pytest.raises(typer.Exit) as exc_info:
            base_space.assert_setup_dev(skip_test=False)
        assert exc_info.value.exit_code == 1
        captured = capsys.readouterr()
        assert "prettier" in captured.err

    def test_assert_setup_dev_skips_test_when_flag_set(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        base_space = BaseSpace()
        mock_ctx.dry_run = True
        with mock_ctx:
            base_space.assert_setup_dev(skip_test=True)
        captured = capsys.readouterr()
        assert "prettier" in captured.err

    def test_update_runs_upgrade_commands(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        base_space = BaseSpace()
        with mock_ctx:
            base_space.update()
        captured = capsys.readouterr()
        assert "uv python upgrade" in captured.err
        assert "uv tool upgrade --all" in captured.err

    @pytest.mark.parametrize(
        "method_name",
        ["test_integration", "test_all"],
    )
    def test_test_methods_call_no_implementation(
        self, method_name: str, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        base_space = BaseSpace()
        with mock_ctx, pytest.raises(typer.Exit):
            getattr(base_space, method_name)()
        captured = capsys.readouterr()
        assert "No implementation" in captured.err

    @pytest.mark.parametrize(
        "platform",
        ["linux", "windows", "other"],
    )
    @patch("bakelib.space.base.get_platform")
    def test_setup_dev_with_unsupported_platform_shows_warning(
        self,
        mock_get_platform: MagicMock,
        platform: str,
        mock_ctx: Context,
        capsys: pytest.CaptureFixture,
    ) -> None:
        mock_get_platform.return_value = platform
        base_space = BaseSpace()
        with mock_ctx, patch.object(mock_ctx, "override_dry_run"):
            base_space.setup_dev()
        captured = capsys.readouterr()
        err = strip_ansi(captured.err)
        assert f"Platform '{platform}' is not supported" in err
        assert "Running in dry-run mode" in err

    def test_not_implemented_raises_not_implemented_error(self) -> None:
        base_space = BaseSpace()
        with pytest.raises(NotImplementedError) as exc_info:
            base_space._not_implemented("test_method")
        assert "BaseSpace must implement test_method()" in str(exc_info.value)

    def test_package_name_raises_not_implemented_error(self, mock_ctx: Context) -> None:
        base_space = BaseSpace()
        with pytest.raises(NotImplementedError) as exc_info, mock_ctx:
            base_space.package_name()
        assert "BaseSpace must implement package_name()" in str(exc_info.value)

    def test_current_version_raises_not_implemented_error(self, mock_ctx: Context) -> None:
        base_space = BaseSpace()
        with pytest.raises(NotImplementedError) as exc_info, mock_ctx:
            base_space.current_version()
        assert "BaseSpace must implement current_version()" in str(exc_info.value)
