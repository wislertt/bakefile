import subprocess
from contextlib import contextmanager

import pytest
import typer
from pydantic import SecretStr

from bake import Context
from bake.ui.logger import strip_ansi
from bakelib.publisher import Publisher
from bakelib.refreshable_cache import ChainedCache, KeyringCache, NullCache, RefreshableCache
from bakelib.space.base import BaseSpace
from bakelib.space.lib import BaseLibSpace, PublishResult, PublishStatus


class MinimalTestPublisher(Publisher):
    """Minimal test publisher for testing BaseLibSpace."""

    valid_registries: tuple[str, ...] = ("test-pypi", "pypi", "crates")

    def _get_publish_token_from_remote(self) -> str | None:
        return None

    def _build_for_publish(self):
        pass

    def _setup_token_env(self, env: dict[str, str], token: str) -> None:
        _ = env, token  # Token not needed for minimal test

    def _execute_publish_command(
        self, env: dict[str, str], token: str | None
    ) -> subprocess.CompletedProcess[str]:
        _ = env, token
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    def _is_auth_failure(self, result: subprocess.CompletedProcess[str]) -> bool:
        _ = result
        return False

    def _is_already_exists_error(self, result: subprocess.CompletedProcess[str]) -> bool:
        _ = result
        return False

    @classmethod
    def _pre_publish_setup(cls, ctx: Context) -> None:
        pass


class MinimalTestLibSpace(BaseLibSpace):
    """Minimal concrete implementation of BaseLibSpace for testing default methods."""

    def get_publish_registries(self) -> set[str]:
        return {"test-pypi", "pypi", "crates"}

    def get_publisher(self, registry: str) -> MinimalTestPublisher:
        return MinimalTestPublisher(self.ctx, registry)

    @property
    def _package_name(self) -> str:
        return "test-package"

    @property
    def _version(self) -> str:
        return "0.0.0"

    @_version.setter
    def _version(self, value: str) -> None:
        _ = value


def test_baselib_space_is_base_space() -> None:
    assert issubclass(BaseLibSpace, BaseSpace)


class TestBaseLibSpace:
    """Tests for BaseLibSpace methods using minimal test subclass."""

    def test_version_bump_context_is_context_manager(self, mock_ctx: Context) -> None:
        space = MinimalTestLibSpace()
        with mock_ctx, space._version_bump_context("1.2.3"):
            pass

    def test_version_bump_context_yields(self, mock_ctx: Context) -> None:
        space = MinimalTestLibSpace()
        with mock_ctx, space._version_bump_context("1.0.0"):
            assert True

    def test_handle_publish_result_exits_on_auth_failed(self, mock_ctx: Context) -> None:
        space = MinimalTestLibSpace()
        result = PublishResult(result=None, status=PublishStatus.AUTH_FAILED)
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
        result = PublishResult(result=successful_dry_run_result, status=PublishStatus.DRY_RUN)

        with mock_ctx:
            space._handle_publish_result(result)
        captured = capsys.readouterr()
        output = strip_ansi(captured.err)
        assert "dry-run" in output.lower()

    def test_handle_publish_result_exits_on_empty_result(self, mock_ctx: Context) -> None:
        space = MinimalTestLibSpace()
        mock_ctx.dry_run = False
        # Result is None with ERROR status - unexpected case
        result = PublishResult(result=None, status=PublishStatus.ERROR)

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
        result = PublishResult(result=success_result, status=PublishStatus.SUCCESS)

        with mock_ctx:
            space._handle_publish_result(result)
        captured = capsys.readouterr()
        output = strip_ansi(captured.err)
        assert "succeeded" in output.lower()

    def test_handle_publish_result_exits_on_nonzero_returncode(self, mock_ctx: Context) -> None:
        space = MinimalTestLibSpace()
        mock_ctx.dry_run = False
        # Failed publish result
        failed_result = subprocess.CompletedProcess(
            args=["publish"], returncode=1, stdout="", stderr="Publish failed"
        )
        result = PublishResult(result=failed_result, status=PublishStatus.ERROR)

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
        result = PublishResult(result=error_result, status=PublishStatus.ERROR)

        with pytest.raises(typer.Exit) as exc_info, mock_ctx:
            space._handle_publish_result(result)
        assert exc_info.value.exit_code == 1

    def test_handle_publish_result_returns_early_on_dry_run(self, mock_ctx: Context) -> None:
        space = MinimalTestLibSpace()
        # mock_ctx.dry_run is True by default, should return early without error
        result = PublishResult(result=None, status=PublishStatus.AUTH_FAILED)

        with mock_ctx:
            # Should not raise Exit because dry_run=True causes early return
            space._handle_publish_result(result)

    def test_handle_publish_result_warns_on_already_exists(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        space = MinimalTestLibSpace()
        mock_ctx.dry_run = False
        exists_result = subprocess.CompletedProcess(
            args=["publish"], returncode=0, stdout="", stderr=""
        )
        result = PublishResult(result=exists_result, status=PublishStatus.ALREADY_EXISTS)

        with mock_ctx:
            space._handle_publish_result(result)
        captured = capsys.readouterr()
        output = strip_ansi(captured.err)
        assert "already exists" in output.lower()

    def test_handle_publish_result_exits_on_unexpected_status(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        space = MinimalTestLibSpace()
        mock_ctx.dry_run = False
        other_result = subprocess.CompletedProcess(
            args=["publish"], returncode=0, stdout="", stderr=""
        )
        result = PublishResult(result=other_result, status=PublishStatus.OTHER)

        with pytest.raises(typer.Exit) as exc_info, mock_ctx:
            space._handle_publish_result(result)
        assert exc_info.value.exit_code == 1
        captured = capsys.readouterr()
        output = strip_ansi(captured.err)
        assert "unexpected publish status" in output.lower()

    def test_execute_publish_returns_result_on_success(
        self, mock_ctx: Context, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fetch_token() -> str | None:
            return "test-token"

        with mock_ctx:
            space = MinimalTestLibSpace()

            backends: list[type[RefreshableCache[str | None]]] = [KeyringCache, NullCache]
            cached_publish_token = ChainedCache(
                backends=backends,
                namespace="test-namespace",
                key="test-key",
                fetch_fn=fetch_token,
            )
            cached_publish_token.set("test-token")

            success_result = subprocess.CompletedProcess(
                args=["publish"], returncode=0, stdout="Success", stderr=""
            )

            publisher = space.get_publisher("test-pypi")
            space._publisher = publisher

            def mock_publish(token: str | None) -> PublishResult:
                _ = token
                return PublishResult(result=success_result, status=PublishStatus.SUCCESS)

            monkeypatch.setattr(publisher, "_publish_with_token", mock_publish)

            result = space._execute_publish(cached_publish_token=cached_publish_token)

        assert result.status == PublishStatus.SUCCESS
        assert result.result is not None
        assert result.result.returncode == 0

    def test_publish_calls_all_methods_in_correct_order(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        # Track method calls
        call_order = []

        # Create a test publisher class that tracks calls
        class TrackingTestPublisher(MinimalTestPublisher):
            @classmethod
            def _pre_publish_setup(cls, ctx: Context) -> None:
                call_order.append("_pre_publish_setup")
                return super()._pre_publish_setup(ctx)

            def _build_for_publish(self):
                call_order.append("_build_for_publish")
                return super()._build_for_publish()

        # Create a test space with tracking
        class TrackingTestLibSpace(MinimalTestLibSpace):
            def get_publisher(self, registry: str) -> TrackingTestPublisher:
                return TrackingTestPublisher(self.ctx, registry)

            def _get_cached_publish_token(self, *args, **kwargs):
                call_order.append("_get_cached_publish_token")
                return super()._get_cached_publish_token(*args, **kwargs)

            def _version_bump_context(
                self,
                version: str | None,
                version_format="semver",
                schema="standard-base-prerelease-post-dev",
            ):
                _ = version, version_format, schema
                call_order.append("_version_bump_context")

                @contextmanager
                def context():
                    call_order.append("_version_bump_context_enter")
                    yield

                return context()

            def _execute_publish(self, cached_publish_token) -> PublishResult:
                _ = cached_publish_token
                call_order.append("_execute_publish")
                success_result = subprocess.CompletedProcess(
                    args=["publish"], returncode=0, stdout="Success", stderr=""
                )
                return PublishResult(result=success_result, status=PublishStatus.SUCCESS)

            def _handle_publish_result(self, *args, **kwargs):
                call_order.append("_handle_publish_result")
                return super()._handle_publish_result(*args, **kwargs)

        with mock_ctx:
            space = TrackingTestLibSpace()
            mock_ctx.dry_run = False

            _ = capsys

            space.publish(registry="test-pypi", token="test-token", version="1.0.0")

        # Verify methods were called in correct order
        assert "_get_cached_publish_token" in call_order
        assert "_pre_publish_setup" in call_order
        assert "_version_bump_context" in call_order
        assert "_build_for_publish" in call_order
        assert "_execute_publish" in call_order
        assert "_handle_publish_result" in call_order

    def test_handle_publish_result_exits_on_unexpected_state(self, mock_ctx: Context) -> None:
        space = MinimalTestLibSpace()
        mock_ctx.dry_run = False

        # Test ERROR status with a result
        error_result = subprocess.CompletedProcess(
            args=["publish"],
            returncode=1,
            stdout="",
            stderr="",
        )
        result = PublishResult(result=error_result, status=PublishStatus.ERROR)

        with pytest.raises(typer.Exit) as exc_info, mock_ctx:
            space._handle_publish_result(result)
        assert exc_info.value.exit_code == 1

    def test_get_cached_publish_token_with_no_local_token(self, mock_ctx: Context) -> None:
        with mock_ctx:
            space = MinimalTestLibSpace()
            publisher = space.get_publisher("test-pypi")
            space._publisher = publisher
            cached_token = space._get_cached_publish_token(token=None, registry="test-pypi")
        cached_token.delete()
        result = cached_token.get_value()
        assert result is None

    def test_get_cached_publish_token_with_local_token(self, mock_ctx: Context) -> None:
        with mock_ctx:
            space = MinimalTestLibSpace()
            publisher = space.get_publisher("test-pypi")
            space._publisher = publisher
            cached_token = space._get_cached_publish_token(
                token="local-token", registry="test-pypi"
            )
        result = cached_token.get_value()
        assert result == "local-token"

    def test_execute_publish_returns_auth_failed_on_refresh_needed_error(
        self, mock_ctx: Context, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fetch_token() -> str | None:
            return "dummy-token"

        with mock_ctx:
            space = MinimalTestLibSpace()

            backends: list[type[RefreshableCache[str | None]]] = [KeyringCache, NullCache]
            cached_publish_token = ChainedCache(
                backends=backends,
                namespace="test-namespace",
                key="test-key",
                fetch_fn=fetch_token,
            )
            cached_publish_token.set("dummy-token")

            publisher = space.get_publisher("test-pypi")
            space._publisher = publisher

            def mock_publish(token: str | None) -> PublishResult:
                _ = token
                failed_result = subprocess.CompletedProcess(
                    args=[],
                    returncode=1,
                    stderr="403 Invalid or non-existent authentication information",
                )
                return PublishResult(result=failed_result, status=PublishStatus.AUTH_FAILED)

            monkeypatch.setattr(publisher, "_publish_with_token", mock_publish)

            result = space._execute_publish(cached_publish_token=cached_publish_token)

        assert result.status == PublishStatus.AUTH_FAILED
        assert result.result is None


class TestBaseLibSpaceSetupTools:
    """Tests for BaseLibSpace.setup_tools method."""

    def test_setup_tools_calls_parent_and_rustup_zerv(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        space = MinimalTestLibSpace()
        with mock_ctx:
            space.setup_tools()
        captured = capsys.readouterr()
        err = strip_ansi(captured.err)

        # Parent setup_tools calls setup_mise, install_mise_tools
        assert "mise install" in err
        assert "mise doctor" in err


class TestBaseLibSpaceGetRequiredCliTools:
    """Tests for BaseLibSpace._get_required_cli_tools method."""

    def test_get_required_cli_tools_inherits_parent_tools(self) -> None:
        space = MinimalTestLibSpace()
        tools = space._get_required_cli_tools()
        # Parent tools from BaseSpace
        assert "bun" in tools
        assert "bakefile" in tools
        assert "pre-commit" in tools

    def test_get_required_cli_tools_adds_zerv(self) -> None:
        space = MinimalTestLibSpace()
        tools = space._get_required_cli_tools()
        assert "zerv" in tools
        assert tools["zerv"] is None  # global tool


class TestBaseLibSpaceSecretIntegration:
    """Tests for BaseLibSpace secret-related methods."""

    def test_get_secret_keys_includes_publish_keys(self) -> None:
        class LibSpaceWithRegistries(MinimalTestLibSpace):
            def get_publish_registries(self) -> set[str]:
                return {"pypi", "test-pypi"}

        space = LibSpaceWithRegistries()
        keys = space.get_secret_keys()
        assert "publish-token-pypi" in keys
        assert "publish-token-test-pypi" in keys

    def test_get_fetch_fn_returns_super_for_non_publish_keys(self) -> None:
        space = MinimalTestLibSpace()
        fetch_fn = space._get_fetch_fn("other-key")
        # Should return null_fetch_fn from parent
        assert fetch_fn() is None

    def test_get_publish_token_returns_token_when_set(self) -> None:
        space = MinimalTestLibSpace()
        space.bake_publish_token = SecretStr("my-token")
        assert space._get_publish_token() == "my-token"

    def test_get_publish_token_returns_none_when_nothing_set(self) -> None:
        space = MinimalTestLibSpace()
        # No token and no publisher
        assert space._get_publish_token() is None

    def test_pre_publish_setup_raises_when_publisher_not_set(self, mock_ctx: Context) -> None:
        space = MinimalTestLibSpace()
        with mock_ctx, pytest.raises(ValueError, match="_publisher is not set"):
            space._pre_publish_setup()

    def test_execute_publish_raises_when_publisher_not_set(self, mock_ctx: Context) -> None:
        space = MinimalTestLibSpace()
        from bakelib.refreshable_cache import ChainedCache, MemoryCache, RefreshableCache

        backends: list[type[RefreshableCache[str | None]]] = [MemoryCache]

        def fetch_fn() -> str | None:
            return None

        cache = ChainedCache(
            backends=backends,
            namespace="test",
            key="test-key",
            fetch_fn=fetch_fn,
        )
        with mock_ctx, pytest.raises(ValueError, match="_publisher is not set"):
            space._execute_publish(cached_publish_token=cache)
