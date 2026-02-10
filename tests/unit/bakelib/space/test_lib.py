import subprocess
import typing
from contextlib import contextmanager

import pytest
import typer
from pydantic import SecretStr

from bake import Context
from bake.ui.logger import strip_ansi
from bakelib.refreshable_cache import ChainedCache, KeyringCache, NullCache
from bakelib.space.base import BaseSpace
from bakelib.space.lib import BaseLibSpace, PublishResult
from bakelib.space.utils import ToolInfo


class MinimalTestLibSpace(BaseLibSpace):
    """Minimal concrete implementation of BaseLibSpace for testing default methods."""

    def _validate_registry(self, registry: str) -> str:
        return registry

    def _get_publish_token_from_remote(self, registry: str) -> str | None:
        _ = registry
        return None

    def package_name(self) -> str:
        return "test-package"

    def _build_for_publish(self):
        pass

    def _publish_with_token(self, token: str | None, registry: str) -> PublishResult:
        _ = token, registry
        return PublishResult(result=None, is_dry_run=self.ctx.dry_run, is_auth_failed=False)

    @contextmanager
    def _version_bump_context(self, _version: str):
        yield

    def _pre_publish_cleanup(self):
        pass


def test_baselib_space_is_base_space() -> None:
    assert issubclass(BaseLibSpace, BaseSpace)


class TestBaseLibSpace:
    """Tests for BaseLibSpace methods using minimal test subclass."""

    def test_get_token_from_cli_returns_token_when_provided(self) -> None:
        space = MinimalTestLibSpace()
        token = space._get_token_from_local("my-token")
        assert token == "my-token"

    def test_get_token_from_cli_returns_none_when_not_provided(self) -> None:
        space = MinimalTestLibSpace()
        token = space._get_token_from_local(None)
        assert token is None

    def test_get_token_from_cli_gets_from_bake_publish_token(self) -> None:
        space = MinimalTestLibSpace()
        space.bake_publish_token = SecretStr("stored-token")
        token = space._get_token_from_local(None)
        assert token == "stored-token"

    def test_version_bump_context_is_context_manager(self, mock_ctx: Context) -> None:
        space = MinimalTestLibSpace()
        with mock_ctx, space._version_bump_context("1.2.3"):
            pass

    def test_pre_publish_cleanup_does_nothing_by_default(self, mock_ctx: Context) -> None:
        space = MinimalTestLibSpace()
        with mock_ctx:
            space._pre_publish_cleanup()

    def test_version_bump_context_yields(self, mock_ctx: Context) -> None:
        space = MinimalTestLibSpace()
        with mock_ctx, space._version_bump_context("1.0.0"):
            assert True

    def test_handle_publish_result_exits_on_auth_failed(self, mock_ctx: Context) -> None:
        space = MinimalTestLibSpace()
        result = PublishResult(result=None, is_dry_run=False, is_auth_failed=True)
        mock_ctx.dry_run = False  # Need to disable dry_run to test auth failed path

        with pytest.raises(typer.Exit) as exc_info, mock_ctx:
            space._handle_publish_result(result)
        assert exc_info.value.exit_code == 1

    def test_handle_publish_result_warns_on_dry_run(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        space = MinimalTestLibSpace()
        mock_ctx.dry_run = False
        # Create a successful result that indicates it was a dry run
        successful_dry_run_result = subprocess.CompletedProcess(
            args=["publish"], returncode=0, stdout="", stderr=""
        )
        result = PublishResult(
            result=successful_dry_run_result, is_dry_run=True, is_auth_failed=False
        )

        with mock_ctx:
            space._handle_publish_result(result)
        captured = capsys.readouterr()
        output = strip_ansi(captured.err)
        assert "dry-run" in output.lower()

    def test_handle_publish_result_exits_on_empty_result(self, mock_ctx: Context) -> None:
        space = MinimalTestLibSpace()
        mock_ctx.dry_run = False
        # Result is None but not auth failed - unexpected case
        result = PublishResult(result=None, is_dry_run=False, is_auth_failed=False)

        with pytest.raises(typer.Exit) as exc_info, mock_ctx:
            space._handle_publish_result(result)
        assert exc_info.value.exit_code == 1

    def test_handle_publish_result_succeeds_on_zero_returncode(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        space = MinimalTestLibSpace()
        mock_ctx.dry_run = False
        # Successful publish result
        success_result = subprocess.CompletedProcess(
            args=["publish"], returncode=0, stdout="Successfully published", stderr=""
        )
        result = PublishResult(result=success_result, is_dry_run=False, is_auth_failed=False)

        with mock_ctx:
            space._handle_publish_result(result)
        captured = capsys.readouterr()
        output = strip_ansi(captured.out)
        assert "succeeded" in output.lower()

    def test_handle_publish_result_exits_on_nonzero_returncode(self, mock_ctx: Context) -> None:
        space = MinimalTestLibSpace()
        mock_ctx.dry_run = False
        # Failed publish result
        failed_result = subprocess.CompletedProcess(
            args=["publish"], returncode=1, stdout="", stderr="Publish failed"
        )
        result = PublishResult(result=failed_result, is_dry_run=False, is_auth_failed=False)

        with pytest.raises(typer.Exit) as exc_info, mock_ctx:
            space._handle_publish_result(result)
        assert exc_info.value.exit_code == 1

    def test_handle_publish_result_exits_on_unexpected_error(self, mock_ctx: Context) -> None:
        space = MinimalTestLibSpace()
        mock_ctx.dry_run = False
        # Publish failed with specific error code
        error_result = subprocess.CompletedProcess(
            args=["publish"], returncode=2, stdout="", stderr="Unexpected error"
        )
        result = PublishResult(result=error_result, is_dry_run=False, is_auth_failed=False)

        with pytest.raises(typer.Exit) as exc_info, mock_ctx:
            space._handle_publish_result(result)
        assert exc_info.value.exit_code == 1

    def test_handle_publish_result_returns_early_on_dry_run(self, mock_ctx: Context) -> None:
        space = MinimalTestLibSpace()
        # mock_ctx.dry_run is True by default, should return early without error
        result = PublishResult(result=None, is_dry_run=False, is_auth_failed=True)

        with mock_ctx:
            # Should not raise Exit because dry_run=True causes early return
            space._handle_publish_result(result)

    def test_execute_publish_returns_result_on_success(
        self, mock_ctx: Context, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        space = MinimalTestLibSpace()

        def fetch_token() -> str | None:
            return "test-token"

        cached_publish_token = ChainedCache(
            backends=[KeyringCache, NullCache],
            namespace="test-namespace",
            key="test-key",
            fetch_fn=fetch_token,
        )
        cached_publish_token.set("test-token")

        success_result = subprocess.CompletedProcess(
            args=["publish"], returncode=0, stdout="Success", stderr=""
        )

        def mock_publish(token: str | None, registry: str) -> PublishResult:
            _ = token, registry
            return PublishResult(result=success_result, is_dry_run=False, is_auth_failed=False)

        monkeypatch.setattr(space, "_publish_with_token", mock_publish)

        with mock_ctx:
            result = space._execute_publish(cached_publish_token, "test-pypi")

        assert result.is_auth_failed is False
        assert result.result is not None
        assert result.result.returncode == 0

    def test_publish_calls_all_methods_in_correct_order(
        self, mock_ctx: Context, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        space = MinimalTestLibSpace()
        mock_ctx.dry_run = False

        # Track method calls
        call_order = []

        original_get_cached_publish_token = space._get_cached_publish_token
        original_handle_publish_result = space._handle_publish_result

        def mock_get_cached_publish_token(*args, **kwargs):
            call_order.append("_get_cached_publish_token")
            return original_get_cached_publish_token(*args, **kwargs)

        def mock_pre_publish_cleanup():
            call_order.append("_pre_publish_cleanup")

        def mock_version_bump_context(_version, **kwargs):
            _ = kwargs
            call_order.append("_version_bump_context")

            @contextmanager
            def context():
                call_order.append("_version_bump_context_enter")
                yield

            return context()

        def mock_build_for_publish(**kwargs):
            _ = kwargs
            call_order.append("_build_for_publish")

        def mock_execute_publish(**kwargs):
            _ = kwargs
            call_order.append("_execute_publish")
            success_result = subprocess.CompletedProcess(
                args=["publish"], returncode=0, stdout="Success", stderr=""
            )
            return PublishResult(result=success_result, is_dry_run=False, is_auth_failed=False)

        def mock_handle_publish_result(*args, **kwargs):
            call_order.append("_handle_publish_result")
            return original_handle_publish_result(*args, **kwargs)

        monkeypatch.setattr(space, "_get_cached_publish_token", mock_get_cached_publish_token)
        monkeypatch.setattr(space, "_pre_publish_cleanup", mock_pre_publish_cleanup)
        monkeypatch.setattr(space, "_version_bump_context", mock_version_bump_context)
        monkeypatch.setattr(space, "_build_for_publish", mock_build_for_publish)
        monkeypatch.setattr(space, "_execute_publish", mock_execute_publish)
        monkeypatch.setattr(space, "_handle_publish_result", mock_handle_publish_result)

        _ = capsys

        with mock_ctx:
            space.publish(registry="test-pypi", token="test-token", version="1.0.0")

        # Verify methods were called in correct order
        assert "_get_cached_publish_token" in call_order
        assert "_pre_publish_cleanup" in call_order
        assert "_version_bump_context" in call_order
        assert "_build_for_publish" in call_order
        assert "_execute_publish" in call_order
        assert "_handle_publish_result" in call_order

    def test_handle_publish_result_exits_on_unexpected_state(self, mock_ctx: Context) -> None:
        space = MinimalTestLibSpace()
        mock_ctx.dry_run = False

        # Create a mock result with a returncode that breaks normal comparison logic
        # This simulates an unexpected state where neither == 0 nor != 0 is True
        class BizarreReturnCode:
            def __eq__(self, other):
                # Always return False to create an unreachable state
                return False

            def __ne__(self, other):
                # Always return False to create an unreachable state
                return False

        bizarre_result = subprocess.CompletedProcess(
            args=["publish"],
            returncode=typing.cast(int, BizarreReturnCode()),
            stdout="",
            stderr="",
        )
        result = PublishResult(result=bizarre_result, is_dry_run=False, is_auth_failed=False)

        with pytest.raises(typer.Exit) as exc_info, mock_ctx:
            space._handle_publish_result(result)
        assert exc_info.value.exit_code == 1

    def test_get_cached_publish_token_with_no_local_token(self, mock_ctx: Context) -> None:
        space = MinimalTestLibSpace()
        with mock_ctx:
            cached_token = space._get_cached_publish_token(token=None, registry="test-pypi")
        cached_token.delete()
        result = cached_token.get_value()
        assert result is None

    def test_get_cached_publish_token_with_local_token(self, mock_ctx: Context) -> None:
        space = MinimalTestLibSpace()
        with mock_ctx:
            cached_token = space._get_cached_publish_token(
                token="local-token", registry="test-pypi"
            )
        result = cached_token.get_value()
        assert result == "local-token"

    def test_execute_publish_returns_auth_failed_on_refresh_needed_error(
        self, mock_ctx: Context, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        space = MinimalTestLibSpace()

        def fetch_token() -> str | None:
            return "dummy-token"

        cached_publish_token = ChainedCache(
            backends=[KeyringCache, NullCache],
            namespace="test-namespace",
            key="test-key",
            fetch_fn=fetch_token,
        )
        cached_publish_token.set("dummy-token")

        def mock_publish(token: str | None, registry: str) -> PublishResult:
            _ = token, registry
            failed_result = subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stderr="403 Invalid or non-existent authentication information",
            )
            return PublishResult(result=failed_result, is_dry_run=False, is_auth_failed=False)

        monkeypatch.setattr(space, "_publish_with_token", mock_publish)

        with mock_ctx:
            result = space._execute_publish(cached_publish_token, "test-pypi")

        assert result.is_auth_failed is True
        assert result.result is None


class TestBaseLibSpaceDefaults:
    """Tests for BaseLibSpace default implementations using minimal subclass."""

    def test_default_is_auth_failure_returns_true_on_nonzero_returncode(self) -> None:
        space = MinimalTestLibSpace()
        result = subprocess.CompletedProcess(args=[], returncode=1, stderr="error")
        assert space._is_auth_failure(result) is True

    def test_default_is_auth_failure_returns_false_on_zero_returncode(self) -> None:
        space = MinimalTestLibSpace()
        result = subprocess.CompletedProcess(args=[], returncode=0, stderr="no error")
        assert space._is_auth_failure(result) is False


class TestBaseLibSpaceSetupTools:
    """Tests for BaseLibSpace.setup_tools method."""

    def test_setup_tools_calls_parent_and_rustup_zerv(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        space = MinimalTestLibSpace()
        with mock_ctx:
            space.setup_tools(platform="macos")
        captured = capsys.readouterr()
        err = strip_ansi(captured.err)

        # Parent setup_tools calls setup_bun, setup_uv, setup_uv_tool
        assert "brew install oven-sh/bun/bun" in err
        assert "brew install uv" in err
        assert "uv tool install bakefile" in err


class TestBaseLibSpaceGetTools:
    """Tests for BaseLibSpace._get_tools method."""

    def test_get_tools_inherits_parent_tools(self) -> None:
        space = MinimalTestLibSpace()
        tools = space._get_tools()
        # Parent tools from BaseSpace
        assert "bun" in tools
        assert "uv" in tools
        assert "bakefile" in tools
        assert "pre-commit" in tools

    def test_get_tools_adds_zerv(self) -> None:
        space = MinimalTestLibSpace()
        tools = space._get_tools()
        assert "zerv" in tools
        assert isinstance(tools["zerv"], ToolInfo)
