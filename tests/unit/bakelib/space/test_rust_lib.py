import subprocess
from pathlib import Path
from typing import get_args

import pytest
import typer

from bake import Context
from bake.ui.logger import strip_ansi
from bakelib.space.lib import PublishResult
from bakelib.space.rust_lib import CratesRegistry, RustLibSpace

_CARGO_TOML_CONTENT = """\
[package]
name = "test-package"
version = "1.0.0"
"""


class TestRustLibSpace:
    def test_validate_registry_returns_valid_indices(self):
        space = RustLibSpace()
        assert space._validate_registry("crates") == "crates"

    def test_validate_registry_raises_error_for_invalid_registry(self):
        space = RustLibSpace()
        with pytest.raises(typer.Exit):
            space._validate_registry("invalid")

    def test_get_publish_token_from_remote_returns_none(self):
        space = RustLibSpace()
        token = space._get_publish_token_from_remote("crates")
        assert token is None

    def test_is_auth_failure_detects_403_error(self):
        space = RustLibSpace()
        result = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stderr="status 403 Forbidden",
        )
        assert space._is_auth_failure(result) is True

    def test_is_auth_failure_detects_401_error(self):
        space = RustLibSpace()
        result = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stderr="status 401 Unauthorized",
        )
        assert space._is_auth_failure(result) is True

    def test_is_auth_failure_returns_false_for_non_auth_errors(self):
        space = RustLibSpace()
        result = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stderr="Some other error",
        )
        assert space._is_auth_failure(result) is False

    def test_is_auth_failure_returns_false_for_success(self):
        space = RustLibSpace()
        result = subprocess.CompletedProcess(args=[], returncode=0, stderr="")
        assert space._is_auth_failure(result) is False

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
        capsys: pytest.CaptureFixture,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that publish handles idempotent case when version already exists."""
        cargo_toml = tmp_path / "Cargo.toml"
        cargo_toml.write_text(_CARGO_TOML_CONTENT)
        monkeypatch.chdir(tmp_path)

        space = RustLibSpace()

        # Mock ctx.run to simulate cargo publish failing due to version already existing
        failed_result = subprocess.CompletedProcess(
            args=["cargo", "publish", "--allow-dirty", "--dry-run"],
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
        with mock_ctx:
            result = space._publish_with_token(token=None, registry="crates")

        # Verify the result was converted to success (idempotent publish)
        assert result.result is not None
        assert result.result.returncode == 0
        captured = capsys.readouterr()
        assert "already exists on crates.io" in captured.out


class TestCratesRegistry:
    def test_crates_registry_literal_contains_crates(self):
        valid_registries = tuple(get_args(CratesRegistry))
        assert "crates" in valid_registries


class TestPublishResult:
    def test_publish_result_fields(self):
        result = PublishResult(
            result=None,
            is_dry_run=False,
            is_auth_failed=False,
        )
        assert result.result is None
        assert result.is_dry_run is False
        assert result.is_auth_failed is False
