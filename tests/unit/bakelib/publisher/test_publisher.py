"""Tests for the Publisher base class."""

import subprocess

import pytest

from bake import Context
from bakelib.publisher import Publisher, PublishStatus


class MinimalTestPublisher(Publisher):
    """Minimal test publisher for testing Publisher base class."""

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


class TestPublisherPrePublishSetup:
    """Tests for Publisher._pre_publish_setup method."""

    def test_pre_publish_setup_does_nothing_by_default(self, mock_ctx: Context) -> None:
        """Test that _pre_publish_setup can be overridden to do nothing."""
        with mock_ctx:
            publisher = MinimalTestPublisher(mock_ctx, "test-pypi")
            publisher._pre_publish_setup(mock_ctx)

    def test_pre_publish_setup_raises_not_implemented_on_base_class(
        self, mock_ctx: Context
    ) -> None:
        """Test that calling _pre_publish_setup on base Publisher raises NotImplementedError."""
        with mock_ctx:
            # Create a minimal publisher that does NOT override _pre_publish_setup
            class IncompletePublisher(Publisher):
                valid_registries = ("test-registry",)

                def _get_publish_token_from_remote(self) -> str | None:
                    return None

                def _build_for_publish(self):
                    pass

                def _setup_token_env(self, env: dict[str, str], token: str) -> None:
                    pass

                def _execute_publish_command(
                    self, env: dict[str, str], token: str | None
                ) -> subprocess.CompletedProcess[str]:
                    _ = env, token
                    return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

                def _is_auth_failure(self, result: subprocess.CompletedProcess[str]) -> bool:
                    _ = result
                    return False

                def _is_already_exists_error(
                    self, result: subprocess.CompletedProcess[str]
                ) -> bool:
                    _ = result
                    return False

            publisher = IncompletePublisher(mock_ctx, "test-registry")

            with pytest.raises(NotImplementedError, match="must be overridden"):
                publisher._pre_publish_setup(mock_ctx)


class TestDeterminePublishResult:
    """Tests for Publisher._determine_publish_result method."""

    def test_returns_dry_run_when_token_is_none(self, mock_ctx: Context) -> None:
        with mock_ctx:
            publisher = MinimalTestPublisher(mock_ctx, "test-pypi")
            result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

            publish_result = publisher._determine_publish_result(token=None, result=result)

        assert publish_result.status == PublishStatus.DRY_RUN

    def test_returns_dry_run_when_token_is_empty_string(self, mock_ctx: Context) -> None:
        """Test that empty string token is treated the same as None (dry-run)."""
        with mock_ctx:
            publisher = MinimalTestPublisher(mock_ctx, "test-pypi")
            result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

            publish_result = publisher._determine_publish_result(token="", result=result)

        assert publish_result.status == PublishStatus.DRY_RUN

    def test_returns_success_on_zero_returncode(self, mock_ctx: Context) -> None:
        with mock_ctx:
            publisher = MinimalTestPublisher(mock_ctx, "test-pypi")
            result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

            publish_result = publisher._determine_publish_result(token="test-token", result=result)

        assert publish_result.status == PublishStatus.SUCCESS

    def test_returns_auth_failed_when_is_auth_failure_true(self, mock_ctx: Context) -> None:
        class AuthFailurePublisher(MinimalTestPublisher):
            def _is_auth_failure(self, result: subprocess.CompletedProcess[str]) -> bool:
                _ = result
                return True

        with mock_ctx:
            publisher = AuthFailurePublisher(mock_ctx, "test-pypi")
            result = subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="auth error"
            )

            publish_result = publisher._determine_publish_result(token="test-token", result=result)

        assert publish_result.status == PublishStatus.AUTH_FAILED

    def test_returns_error_on_nonzero_returncode(self, mock_ctx: Context) -> None:
        with mock_ctx:
            publisher = MinimalTestPublisher(mock_ctx, "test-pypi")
            result = subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr="some error"
            )

            publish_result = publisher._determine_publish_result(token="test-token", result=result)

        assert publish_result.status == PublishStatus.ERROR

    def test_returns_already_exists_when_is_already_exists_true(self, mock_ctx: Context) -> None:
        class AlreadyExistsPublisher(MinimalTestPublisher):
            def _is_already_exists_error(self, result: subprocess.CompletedProcess[str]) -> bool:
                _ = result
                return True

        with mock_ctx:
            publisher = AlreadyExistsPublisher(mock_ctx, "test-pypi")
            result = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="exists")

            publish_result = publisher._determine_publish_result(token="test-token", result=result)

        assert publish_result.status == PublishStatus.ALREADY_EXISTS


class TestPublishWithToken:
    """Tests for Publisher._publish_with_token method."""

    def test_uses_dummy_token_when_token_is_none(self, mock_ctx: Context) -> None:
        """Test that None token results in dry-run status."""
        with mock_ctx:
            publisher = MinimalTestPublisher(mock_ctx, "test-pypi")
            publish_result = publisher._publish_with_token(token=None)

        assert publish_result.status == PublishStatus.DRY_RUN

    def test_uses_dummy_token_when_token_is_empty_string(self, mock_ctx: Context) -> None:
        """Test that empty string token is treated as None and results in dry-run status."""
        with mock_ctx:
            publisher = MinimalTestPublisher(mock_ctx, "test-pypi")
            publish_result = publisher._publish_with_token(token="")

        assert publish_result.status == PublishStatus.DRY_RUN

    def test_uses_real_token_when_token_is_non_empty(self, mock_ctx: Context) -> None:
        """Test that non-empty token is used directly."""
        with mock_ctx:
            publisher = MinimalTestPublisher(mock_ctx, "test-pypi")
            publish_result = publisher._publish_with_token(token="real-token")

        assert publish_result.status == PublishStatus.SUCCESS
