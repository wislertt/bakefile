"""Tests for the CratesPublisher error classification."""

import subprocess

from bakelib.publisher.crates import CratesPublisher


def _result(returncode: int, stderr: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout="", stderr=stderr)


class TestIsAlreadyExistsError:
    """Tests for CratesPublisher._is_already_exists_error."""

    def test_detects_single_line_already_exists_error(self) -> None:
        publisher = CratesPublisher("crates")
        stderr = "error: failed to publish\ncaused by: crate `bake` already exists on crates.io\n"

        assert publisher._is_already_exists_error(_result(1, stderr)) is True

    def test_detects_wrapped_already_exists_error(self) -> None:
        publisher = CratesPublisher("crates")
        stderr = "error: failed to publish\ncaused by: crate `bake` already exists\non crates.io\n"

        assert publisher._is_already_exists_error(_result(1, stderr)) is True

    def test_ignores_auth_failure(self) -> None:
        publisher = CratesPublisher("crates")
        stderr = "error: failed to publish\n  status 403 Forbidden\n"

        assert publisher._is_already_exists_error(_result(1, stderr)) is False

    def test_ignores_clean_success(self) -> None:
        publisher = CratesPublisher("crates")
        stderr = "    Publishing bake v0.1.0\n    Uploaded bake v0.1.0\n"

        assert publisher._is_already_exists_error(_result(0, stderr)) is False
