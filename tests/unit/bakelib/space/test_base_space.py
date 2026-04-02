from contextlib import suppress
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
import typer

from bake import Context
from bake.ui.logger import strip_ansi
from bakelib.space.base import BaseSpace


class MinimalTestSpace(BaseSpace):
    @property
    def _package_name(self) -> str:
        return "test-package"

    @property
    def _version(self) -> str:
        return self._version_value

    @_version.setter
    def _version(self, value: str) -> None:
        self._version_setter(value)

    def _version_setter(self, value: str) -> None:
        self._version_value = value


class ChildMinimalTestSpace(MinimalTestSpace):
    """Simulates downstream class (e.g. ARDockerUtils) extending _version setter.

    Only overrides _version_setter — no property getter/setter override needed.
    super()._version_setter(value) works naturally via MRO.
    """

    _extra_tag: str | None = None

    def _version_setter(self, value: str) -> None:
        super()._version_setter(value)
        if self._extra_tag is None:
            self._extra_tag = f"tag-{value}"


class TestBareBaseSpace:
    def test_package_name_raises_not_implemented(self) -> None:
        base_space = BaseSpace()
        with pytest.raises(NotImplementedError, match="BaseSpace must implement _package_name"):
            _ = base_space._package_name

    def test_version_getter_raises_not_implemented(self) -> None:
        base_space = BaseSpace()
        with pytest.raises(NotImplementedError, match="BaseSpace must implement _version"):
            _ = base_space._version

    def test_version_setter_raises_not_implemented(self) -> None:
        base_space = BaseSpace()
        with pytest.raises(NotImplementedError, match="BaseSpace must implement _version"):
            base_space._version = "1.0.0"


class TestBaseSpace:
    def test_version_command_shows_version_when_no_argument_provided(self) -> None:
        base_space = MinimalTestSpace()
        base_space._version = "1.0.0"
        base_space.version()
        assert base_space._version == "1.0.0"

    def test_version_command_sets_version(self) -> None:
        base_space = MinimalTestSpace()
        base_space.version(version="2.0.0")
        assert base_space._version == "2.0.0"


class TestMethodNotAvailable:
    def test_method_not_available_raises_not_implemented(self) -> None:
        base_space = BaseSpace()
        with pytest.raises(NotImplementedError, match="BaseSpace must implement test_method"):
            base_space._method_not_available("test_method")


class TestCommandNotAvailable:
    def test_command_not_available_exits_with_code_1(self, mock_ctx: Context) -> None:
        base_space = MinimalTestSpace()
        with mock_ctx:
            with pytest.raises(typer.Exit) as exc_info:
                base_space._command_not_available("test_command")
            assert exc_info.value.exit_code == 1


class TestDetermineNewVersion:
    def test_determine_new_version_with_explicit_version(self) -> None:
        base_space = MinimalTestSpace()
        result = base_space._determine_new_version(version="1.2.3")
        assert result == "1.2.3"

    def test_determine_new_version_without_version_uses_flow(self) -> None:
        base_space = MinimalTestSpace()
        with patch("bakelib.space.base.zerv") as mock_zerv:
            mock_zerv.flow.return_value = "1.0.1"
            result = base_space._determine_new_version(version=None)
            assert result == "1.0.1"
            mock_zerv.flow.assert_called_once()

    def test_determine_new_version_with_render(self) -> None:
        base_space = MinimalTestSpace()
        with patch("bakelib.space.base.zerv") as mock_zerv:
            mock_zerv.render.return_value = "2.0.0"
            result = base_space._determine_new_version(version="2.0.0")
            assert result == "2.0.0"
            mock_zerv.render.assert_called_once()


class TestVersionBumpContext:
    def test_version_bump_context_restores_original_version(self) -> None:
        base_space = MinimalTestSpace()
        base_space._version = "1.0.0"

        with patch("bakelib.space.base.zerv") as mock_zerv:
            mock_zerv.render.return_value = "2.0.0"

            with base_space._version_bump_context(version="2.0.0"):
                assert base_space._version == "2.0.0"

            assert base_space._version == "1.0.0"

    def test_version_bump_context_restores_on_exception(self) -> None:
        base_space = MinimalTestSpace()
        base_space._version = "1.0.0"

        with patch("bakelib.space.base.zerv") as mock_zerv:
            mock_zerv.render.return_value = "2.0.0"

            try:
                with base_space._version_bump_context(version="2.0.0"):
                    assert base_space._version == "2.0.0"
                    raise ValueError("test error")
            except ValueError:
                pass

            assert base_space._version == "1.0.0"


class TestCommandsNotAvailable:
    def test_command_not_available(self, mock_ctx: Context) -> None:
        base_space = MinimalTestSpace()
        with mock_ctx:
            with pytest.raises(typer.Exit) as exc_info:
                base_space.test()
            assert exc_info.value.exit_code == 1

    def test_test_integration_command_not_available(self, mock_ctx: Context) -> None:
        base_space = MinimalTestSpace()
        with mock_ctx:
            with pytest.raises(typer.Exit) as exc_info:
                base_space.test_integration()
            assert exc_info.value.exit_code == 1

    def test_test_all_command_not_available(self, mock_ctx: Context) -> None:
        base_space = MinimalTestSpace()
        with mock_ctx:
            with pytest.raises(typer.Exit) as exc_info:
                base_space.test_all()
            assert exc_info.value.exit_code == 1


class TestToolsCommand:
    def test_tools_command_outputs_names_by_default(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        base_space = MinimalTestSpace()
        with mock_ctx:
            base_space.tools()
        captured = capsys.readouterr()
        output = strip_ansi(captured.out)
        assert "bun" in output
        assert "zerv" in output
        assert "bakefile" in output

    def test_tools_command_outputs_json_when_flag_set(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        base_space = MinimalTestSpace()
        with mock_ctx:
            base_space.tools(json=True)
        captured = capsys.readouterr()
        output = strip_ansi(captured.out)
        assert "bun" in output
        assert "zerv" in output
        assert "null" in output  # null for global tools


class TestAssertWhichPath:
    def test_assert_which_path_returns_true_in_dry_run(self, mock_ctx: Context) -> None:
        base_space = MinimalTestSpace()
        with mock_ctx:
            result = base_space._assert_which_path("test", None)
            assert result is True

    def test_assert_which_path_returns_true_when_path_matches(self, mock_ctx: Context) -> None:
        base_space = MinimalTestSpace()
        path_prefixes = {Path("/usr/bin")}
        with mock_ctx, patch("bakelib.space.base.shutil.which", return_value="/usr/bin/test"):
            mock_ctx.dry_run = False
            result = base_space._assert_which_path("test", path_prefixes)
            assert result is True

    def test_assert_which_path_returns_false_when_path_does_not_match(
        self, mock_ctx: Context
    ) -> None:
        base_space = MinimalTestSpace()
        path_prefixes = {Path("/usr/bin")}
        with mock_ctx, patch("bakelib.space.base.shutil.which", return_value="/wrong/path/test"):
            mock_ctx.dry_run = False
            result = base_space._assert_which_path("test", path_prefixes)
            assert result is False

    def test_assert_which_path_returns_false_when_tool_not_found(self, mock_ctx: Context) -> None:
        base_space = MinimalTestSpace()
        with mock_ctx, patch("bakelib.space.base.shutil.which", return_value=None):
            mock_ctx.dry_run = False
            result = base_space._assert_which_path("nonexistent", None)
            assert result is False

    def test_assert_which_path_returns_true_for_global_tool(self, mock_ctx: Context) -> None:
        base_space = MinimalTestSpace()
        with mock_ctx, patch("bakelib.space.base.shutil.which", return_value="/usr/bin/some-tool"):
            mock_ctx.dry_run = False
            result = base_space._assert_which_path("some-tool", None)  # None = global tool
            assert result is True


class TestAssertSetupDev:
    def test_assert_setup_dev_with_fast_1_skips_test(self, mock_ctx: Context) -> None:
        base_space = MinimalTestSpace()
        mock_result = MagicMock()
        mock_result.stdout = "/usr/bin/test"

        with mock_ctx, patch.object(mock_ctx, "run", return_value=mock_result):
            mock_ctx.dry_run = True
            with patch.object(type(base_space), "lint") as mock_lint:
                base_space.assert_setup_dev(fast=1)
                mock_lint.assert_called_once()

    def test_assert_setup_dev_with_fast_0_runs_all(self, mock_ctx: Context) -> None:
        base_space = MinimalTestSpace()
        mock_result = MagicMock()
        mock_result.stdout = "/usr/bin/test"

        with mock_ctx, patch.object(mock_ctx, "run", return_value=mock_result):
            mock_ctx.dry_run = True
            with (
                patch.object(type(base_space), "lint") as mock_lint,
                patch.object(type(base_space), "test") as mock_test,
                suppress(typer.Exit),
            ):
                base_space.assert_setup_dev(fast=0)
                mock_lint.assert_called_once()
                mock_test.assert_called_once()

    def test_assert_setup_dev_with_fast_2_skips_test_and_lint(self, mock_ctx: Context) -> None:
        base_space = MinimalTestSpace()
        mock_result = MagicMock()
        mock_result.stdout = "/usr/bin/test"

        with mock_ctx, patch.object(mock_ctx, "run", return_value=mock_result):
            mock_ctx.dry_run = True
            with (
                patch.object(type(base_space), "lint") as mock_lint,
                patch.object(type(base_space), "test") as mock_test,
            ):
                base_space.assert_setup_dev(fast=2)
                mock_lint.assert_not_called()
                mock_test.assert_not_called()


class TestSetupDev:
    def test_setup_dev_shows_warning_on_non_macos(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        base_space = MinimalTestSpace()

        with patch("bakelib.space.base.get_platform", return_value="linux"), mock_ctx:
            base_space.setup_dev()

        captured = capsys.readouterr()
        err = strip_ansi(captured.err)
        assert "dry-run mode" in err.lower()


class TestLint:
    def test_lint_runs_bakefile_lint_when_standalone(self, mock_ctx: Context) -> None:
        base_space = MinimalTestSpace()
        mock_ctx.dry_run = True

        run_calls: list[str] = []

        def capture_run(cmd: str, **_: object) -> None:
            run_calls.append(cmd)

        with (
            mock_ctx,
            patch.object(mock_ctx, "run", side_effect=capture_run),
            patch.object(
                type(mock_ctx.obj), "is_standalone_bakefile", new_callable=PropertyMock
            ) as mock_prop,
        ):
            mock_prop.return_value = True
            base_space.lint()

        assert "bakefile lint" in run_calls

    def test_lint_skips_bakefile_lint_when_not_standalone(self, mock_ctx: Context) -> None:
        base_space = MinimalTestSpace()
        mock_ctx.dry_run = True

        run_calls: list[str] = []

        def capture_run(cmd: str, **_: object) -> None:
            run_calls.append(cmd)

        with (
            mock_ctx,
            patch.object(mock_ctx, "run", side_effect=capture_run),
            patch.object(
                type(mock_ctx.obj), "is_standalone_bakefile", new_callable=PropertyMock
            ) as mock_prop,
        ):
            mock_prop.return_value = False
            base_space.lint()

        assert "bakefile lint" not in run_calls


class TestUpdate:
    def test_update_runs_bakefile_commands_when_standalone(self, mock_ctx: Context) -> None:
        base_space = MinimalTestSpace()
        mock_ctx.dry_run = True

        run_calls: list[str] = []

        def capture_run(cmd: str, **_: object) -> None:
            run_calls.append(cmd)

        with (
            mock_ctx,
            patch("bakelib.space.base.get_platform", return_value="linux"),
            patch.object(mock_ctx, "run", side_effect=capture_run),
            patch.object(
                type(mock_ctx.obj), "is_standalone_bakefile", new_callable=PropertyMock
            ) as mock_prop,
        ):
            mock_prop.return_value = True
            base_space.update()

        assert "bakefile lock --upgrade" in run_calls
        assert "bakefile sync" in run_calls

    def test_update_skips_bakefile_commands_when_not_standalone(self, mock_ctx: Context) -> None:
        base_space = MinimalTestSpace()
        mock_ctx.dry_run = True

        run_calls: list[str] = []

        def capture_run(cmd: str, **_: object) -> None:
            run_calls.append(cmd)

        with (
            mock_ctx,
            patch("bakelib.space.base.get_platform", return_value="linux"),
            patch.object(mock_ctx, "run", side_effect=capture_run),
            patch.object(
                type(mock_ctx.obj), "is_standalone_bakefile", new_callable=PropertyMock
            ) as mock_prop,
        ):
            mock_prop.return_value = False
            base_space.update()

        assert "bakefile lock --upgrade" not in run_calls
        assert "bakefile sync" not in run_calls


class TestSetupProject:
    def test_setup_project_runs_bakefile_sync_when_standalone(self, mock_ctx: Context) -> None:
        base_space = MinimalTestSpace()
        mock_ctx.dry_run = True

        run_calls: list[str] = []

        def capture_run(cmd: str, **_: object) -> None:
            run_calls.append(cmd)

        with (
            mock_ctx,
            patch.object(mock_ctx, "run", side_effect=capture_run),
            patch.object(
                type(mock_ctx.obj), "is_standalone_bakefile", new_callable=PropertyMock
            ) as mock_prop,
        ):
            mock_prop.return_value = True
            base_space.setup_project()

        assert "pre-commit install" in run_calls
        assert "bakefile sync --frozen" in run_calls

    def test_setup_project_skips_bakefile_sync_when_not_standalone(self, mock_ctx: Context) -> None:
        base_space = MinimalTestSpace()
        mock_ctx.dry_run = True

        run_calls: list[str] = []

        def capture_run(cmd: str, **_: object) -> None:
            run_calls.append(cmd)

        with (
            mock_ctx,
            patch.object(mock_ctx, "run", side_effect=capture_run),
            patch.object(
                type(mock_ctx.obj), "is_standalone_bakefile", new_callable=PropertyMock
            ) as mock_prop,
        ):
            mock_prop.return_value = False
            base_space.setup_project()

        assert "pre-commit install" in run_calls
        assert "bakefile sync --frozen" not in run_calls


class TestChildVersionSetterExtensibility:
    """Demonstrates the MRO hack currently required to extend _version setter.

    When a child class overrides @_version.setter, it cannot call the parent
    setter via super() because super()._version invokes the getter (returns a
    string), not the property descriptor. The only workaround is walking the
    MRO manually — this test documents that ugly but necessary hack.
    """

    def test_child_setter_runs_parent_logic(self) -> None:
        child = ChildMinimalTestSpace()
        child._version = "1.2.3"

        assert child._version == "1.2.3"

    def test_child_setter_runs_own_logic(self) -> None:
        child = ChildMinimalTestSpace()
        child._version = "1.2.3"

        assert child._extra_tag == "tag-1.2.3"

    def test_child_setter_does_not_overwrite_existing_tag(self) -> None:
        child = ChildMinimalTestSpace()
        child._extra_tag = "existing-tag"
        child._version = "2.0.0"

        assert child._extra_tag == "existing-tag"

    def test_version_bump_context_works_with_child_setter(self) -> None:
        child = ChildMinimalTestSpace()
        child._version = "1.0.0"
        child._extra_tag = "tag-1.0.0"

        with patch("bakelib.space.base.zerv") as mock_zerv:
            mock_zerv.render.return_value = "2.0.0"

            with child._version_bump_context(version="2.0.0"):
                assert child._version == "2.0.0"
                # _extra_tag should NOT change — it was already set
                assert child._extra_tag == "tag-1.0.0"

        assert child._version == "1.0.0"
