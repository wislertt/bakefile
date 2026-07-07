import subprocess
from pathlib import Path
from typing import get_args

import pytest
import typer

from bake import Context
from bake.ui.logger import strip_ansi
from bakelib.publisher import PublishResult, PublishStatus
from bakelib.publisher.crates import CratesRegistry
from bakelib.space.rust_lib import RustLibSpace

_CARGO_TOML_CONTENT = """\
[package]
name = "test-package"
version = "1.0.0"
"""


class TestRustLibSpaceGetPublishRegistries:
    def test_get_publish_registries_returns_crates_registry(self) -> None:
        space = RustLibSpace()
        registries = space.get_publish_registries()
        assert "crates" in registries


class TestCratesPublisher:
    def test_validate_registry_returns_valid_indices(self, mock_ctx: Context):
        with mock_ctx:
            space = RustLibSpace()
            publisher = space.get_publisher("crates")
            assert publisher.registry == "crates"

    def test_validate_registry_raises_error_for_invalid_registry(self, mock_ctx: Context):
        with mock_ctx:
            space = RustLibSpace()
            with pytest.raises(typer.Exit):
                space.get_publisher("invalid")

    def test_get_publish_token_from_remote_returns_none(self, mock_ctx: Context):
        with mock_ctx:
            space = RustLibSpace()
            publisher = space.get_publisher("crates")
            token = publisher._get_publish_token_from_remote()
            assert token is None

    def test_is_auth_failure_detects_403_error(self, mock_ctx: Context):
        with mock_ctx:
            space = RustLibSpace()
            publisher = space.get_publisher("crates")
            result = subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stderr="status 403 Forbidden",
            )
            assert publisher._is_auth_failure(result) is True

    def test_is_auth_failure_detects_401_error(self, mock_ctx: Context):
        with mock_ctx:
            space = RustLibSpace()
            publisher = space.get_publisher("crates")
            result = subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stderr="status 401 Unauthorized",
            )
            assert publisher._is_auth_failure(result) is True

    def test_is_auth_failure_returns_false_for_non_auth_errors(self, mock_ctx: Context):
        with mock_ctx:
            space = RustLibSpace()
            publisher = space.get_publisher("crates")
            result = subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stderr="Some other error",
            )
            assert publisher._is_auth_failure(result) is False

    def test_is_auth_failure_returns_false_for_success(self, mock_ctx: Context):
        with mock_ctx:
            space = RustLibSpace()
            publisher = space.get_publisher("crates")
            result = subprocess.CompletedProcess(args=[], returncode=0, stderr="")
            assert publisher._is_auth_failure(result) is False

    def test_publish_runs_cargo_publish(
        self,
        mock_ctx: Context,
        capsys: pytest.CaptureFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        cargo_toml = tmp_path / "Cargo.toml"
        cargo_toml.write_text(_CARGO_TOML_CONTENT)
        monkeypatch.chdir(tmp_path)

        space = RustLibSpace()
        with mock_ctx:
            space.publish(registry="crates", token=None, version="1.0.0")
        captured = capsys.readouterr()
        capture_err = strip_ansi(captured.err)
        assert "cargo publish" in capture_err

    def test_publish_with_token_runs_cargo_publish(
        self,
        mock_ctx: Context,
        capsys: pytest.CaptureFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        cargo_toml = tmp_path / "Cargo.toml"
        cargo_toml.write_text(_CARGO_TOML_CONTENT)
        monkeypatch.chdir(tmp_path)

        space = RustLibSpace()
        with mock_ctx:
            space.publish(registry="crates", token="test-token", version="1.0.0")
        captured = capsys.readouterr()
        capture_err = strip_ansi(captured.err)
        assert "cargo publish" in capture_err

    def test_publish_handles_version_already_exists(
        self,
        mock_ctx: Context,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that publish handles idempotent case when version already exists."""
        cargo_toml = tmp_path / "Cargo.toml"
        cargo_toml.write_text(_CARGO_TOML_CONTENT)
        monkeypatch.chdir(tmp_path)

        with mock_ctx:
            space = RustLibSpace()
            publisher = space.get_publisher("crates")

            # Mock ctx.run to simulate cargo publish failing due to version already existing
            failed_result = subprocess.CompletedProcess(
                args=["cargo", "publish", "--allow-dirty"],
                returncode=1,
                stdout="",
                stderr=(
                    "error: failed to publish to registry `crates-io`\n\n"
                    "Caused by:\n  the crate `test-package` v1.0.0 "
                    "already exists on crates.io"
                ),
            )

            # Create a properly typed mock function
            def mock_run(*_, **__) -> subprocess.CompletedProcess[str]:
                return failed_result

            monkeypatch.setattr(mock_ctx, "run", mock_run)
            result = publisher._publish_with_token(mock_ctx, token="test-token")

        # Verify the result indicates already exists (idempotent publish)
        assert result.result is not None
        assert result.status == PublishStatus.ALREADY_EXISTS


class TestCratesRegistry:
    def test_crates_registry_literal_contains_crates(self):
        valid_registries = tuple(get_args(CratesRegistry))
        assert "crates" in valid_registries


class TestPublishResult:
    def test_publish_result_fields(self):
        result = PublishResult(
            result=None,
            status=PublishStatus.SUCCESS,
        )
        assert result.result is None
        assert result.status == PublishStatus.SUCCESS
