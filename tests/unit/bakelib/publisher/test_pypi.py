"""Tests for the PyPIPublisher error classification."""

import subprocess

from bakelib.publisher.pypi import PyPIPublisher

# Captured from a real CI failure: uv wraps its error output at terminal
# width, splitting the "File already exists" phrase across lines.
WRAPPED_ALREADY_EXISTS_400 = """Publishing 1 file to https://upload.pypi.org/legacy/
Uploading zerv_version-0.8.40-py3-none-musllinux_1_2_x86_64.whl (2.2MiB)
error: Failed to publish
       `dist/zerv_version-0.8.40-py3-none-musllinux_1_2_x86_64.whl` to
       `https://upload.pypi.org/legacy/`
  cause: Server returned status code 400 Bad Request. Server says: 400 File
         already exists ('zerv_version-0.8.40-py3-none-musllinux_1_2_x86_64.whl',
         with blake2_256 hash
         '234a0151ce768544bae30527f942681fd4968b089f77706a02f3be7f90c5b654'). See
         https://docs.pypi.org/publishing/troubleshooting/
"""


def _result(returncode: int, stderr: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout="", stderr=stderr)


class TestIsAlreadyExistsError:
    """Tests for PyPIPublisher._is_already_exists_error."""

    def test_detects_wrapped_already_exists_error(self) -> None:
        publisher = PyPIPublisher("pypi")
        result = _result(2, WRAPPED_ALREADY_EXISTS_400)

        assert publisher._is_already_exists_error(result) is True

    def test_detects_single_line_already_exists_error(self) -> None:
        publisher = PyPIPublisher("pypi")
        stderr = "error: Failed to publish\n       Server says: 400 File already exists\n"

        assert publisher._is_already_exists_error(_result(2, stderr)) is True

    def test_detects_content_mismatch_error(self) -> None:
        publisher = PyPIPublisher("pypi")
        stderr = (
            "error: Failed to publish\n  Server says: 400 Local file and index file do not match\n"
        )

        assert publisher._is_already_exists_error(_result(2, stderr)) is True

    def test_detects_skip_existing_warning_on_success(self) -> None:
        publisher = PyPIPublisher("test-pypi")
        stderr = "warning: zerv_version-0.8.40-py3-none-any.whl already exists, skipping\n"

        assert publisher._is_already_exists_error(_result(0, stderr)) is True

    def test_ignores_auth_failure(self) -> None:
        publisher = PyPIPublisher("pypi")
        stderr = "error: Failed to publish\n  Server says: 403 Forbidden\n"

        assert publisher._is_already_exists_error(_result(2, stderr)) is False

    def test_ignores_clean_success(self) -> None:
        publisher = PyPIPublisher("pypi")
        stderr = "Published 1 file to https://upload.pypi.org/legacy/\n"

        assert publisher._is_already_exists_error(_result(0, stderr)) is False
