import subprocess
from contextlib import contextmanager
from unittest import mock

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
        with space._set_ctx(mock_ctx), space._version_bump_context("1.2.3"):
            pass

    def test_pre_publish_cleanup_does_nothing_by_default(self, mock_ctx: Context) -> None:
        space = MinimalTestLibSpace()
        with space._set_ctx(mock_ctx):
            space._pre_publish_cleanup()

    def test_determine_version_returns_version_when_provided(self, mock_ctx: Context) -> None:
        space = MinimalTestLibSpace()
        with space._set_ctx(mock_ctx):
            version = space._determine_version("2.0.0")
        assert version == "2.0.0"

    def test_version_bump_context_yields(self, mock_ctx: Context) -> None:
        space = MinimalTestLibSpace()
        with space._set_ctx(mock_ctx), space._version_bump_context("1.0.0"):
            assert True

    def test_handle_publish_result_exits_on_auth_failed(self, mock_ctx: Context) -> None:
        space = MinimalTestLibSpace()
        result = PublishResult(result=None, is_dry_run=False, is_auth_failed=True)

        with pytest.raises(typer.Exit) as exc_info, space._set_ctx(mock_ctx):
            space._handle_publish_result(result)
        assert exc_info.value.exit_code == 1

    def test_handle_publish_result_warns_on_dry_run(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        space = MinimalTestLibSpace()
        mock_ctx.dry_run = False
        result = PublishResult(result=None, is_dry_run=True, is_auth_failed=False)

        with space._set_ctx(mock_ctx):
            space._handle_publish_result(result)
        captured = capsys.readouterr()
        output = strip_ansi(captured.err)
        assert "dry-run" in output.lower()

    def test_get_cached_publish_token_with_no_local_token(self, mock_ctx: Context) -> None:
        space = MinimalTestLibSpace()
        with space._set_ctx(mock_ctx):
            cached_token = space._get_cached_publish_token(token=None, registry="testpypi")
        cached_token.delete()
        result = cached_token.get_value()
        assert result is None

    def test_get_cached_publish_token_with_local_token(self, mock_ctx: Context) -> None:
        space = MinimalTestLibSpace()
        with space._set_ctx(mock_ctx):
            cached_token = space._get_cached_publish_token(token="local-token", registry="testpypi")
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

        with space._set_ctx(mock_ctx):
            result = space._execute_publish(cached_publish_token, "testpypi")

        assert result.is_auth_failed is True
        assert result.result is None

    def test_determine_version_calls_zerv_when_no_version(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _ = capsys
        space = MinimalTestLibSpace()

        mock_result = subprocess.CompletedProcess(
            args=["zerv flow"],
            returncode=0,
            stdout="0.1.0",
            stderr="",
        )

        mock_run = mock.Mock(return_value=mock_result)
        monkeypatch.setattr(mock_ctx, "run", mock_run)

        with space._set_ctx(mock_ctx):
            version = space._determine_version(None)

        assert version == "0.1.0"
        mock_run.assert_called_once_with("zerv flow", dry_run=False)


class TestBaseLibSpaceDefaults:
    """Tests for BaseLibSpace default implementations using minimal subclass."""

    def test_default_version_schema_returns_none(self) -> None:
        space = MinimalTestLibSpace()
        assert space._version_schema is None

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
        with space._set_ctx(mock_ctx):
            space.setup_tools(platform="macos")
        captured = capsys.readouterr()
        err = strip_ansi(captured.err)

        # Parent setup_tools calls setup_bun, setup_uv, setup_uv_tool
        assert "brew install oven-sh/bun/bun" in err
        assert "brew install uv" in err
        assert "uv tool install bakefile" in err
        # Additional calls from BaseLibSpace
        assert "brew install rustup" in err
        assert "rustup update" in err
        assert "cargo install zerv" in err


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
