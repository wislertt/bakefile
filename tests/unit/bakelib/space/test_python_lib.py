import subprocess

import pytest
import typer

from bake import Context
from bake.ui.logger import strip_ansi
from bakelib.publisher import PublishResult, PublishStatus
from bakelib.space.python_lib import PythonLibSpace


class TestPythonLibSpaceGetPublishRegistries:
    def test_get_publish_registries_returns_pypi_registries(self) -> None:
        space = PythonLibSpace()
        registries = space.get_publish_registries()
        assert "pypi" in registries
        assert "test-pypi" in registries


class TestPyPIPublisher:
    def test_validate_registry_returns_valid_indices(self, mock_ctx: Context):
        with mock_ctx:
            space = PythonLibSpace()
            publisher = space.get_publisher("test-pypi")
            assert publisher.registry == "test-pypi"
            publisher = space.get_publisher("pypi")
            assert publisher.registry == "pypi"

    def test_validate_registry_raises_error_for_invalid_registry(self, mock_ctx: Context):
        with mock_ctx:
            space = PythonLibSpace()
            with pytest.raises(typer.Exit):
                space.get_publisher("invalid")

    def test_get_publish_token_from_remote_returns_none(self, mock_ctx: Context):
        with mock_ctx:
            space = PythonLibSpace()
            publisher = space.get_publisher("test-pypi")
            token = publisher._get_publish_token_from_remote()
            assert token is None

    def test_is_auth_failure_detects_403_error(self, mock_ctx: Context):
        with mock_ctx:
            space = PythonLibSpace()
            publisher = space.get_publisher("test-pypi")
            result = subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stderr="403 Invalid or non-existent authentication information",
            )
            assert publisher._is_auth_failure(result) is True

    def test_is_auth_failure_returns_false_for_non_403_errors(self, mock_ctx: Context):
        with mock_ctx:
            space = PythonLibSpace()
            publisher = space.get_publisher("test-pypi")
            result = subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stderr="Some other error",
            )
            assert publisher._is_auth_failure(result) is False

    def test_is_auth_failure_returns_false_for_success(self, mock_ctx: Context):
        with mock_ctx:
            space = PythonLibSpace()
            publisher = space.get_publisher("test-pypi")
            result = subprocess.CompletedProcess(args=[], returncode=0, stderr="")
            assert publisher._is_auth_failure(result) is False

    def test_is_already_exists_error_detects_already_exists_skipping(self, mock_ctx: Context):
        """Case 1: returncode=0 with 'already exists, skipping' message."""
        with mock_ctx:
            space = PythonLibSpace()
            publisher = space.get_publisher("test-pypi")
            result = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stderr="File already exists, skipping upload",
            )
            assert publisher._is_already_exists_error(result) is True

    def test_is_already_exists_error_detects_different_hash_error(self, mock_ctx: Context):
        """Case 2: returncode!=0 with 'Local file and index file do not match' message."""
        with mock_ctx:
            space = PythonLibSpace()
            publisher = space.get_publisher("test-pypi")
            result = subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stderr="Local file and index file do not match",
            )
            assert publisher._is_already_exists_error(result) is True

    def test_is_already_exists_error_returns_false_for_other_errors(self, mock_ctx: Context):
        with mock_ctx:
            space = PythonLibSpace()
            publisher = space.get_publisher("test-pypi")
            result = subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stderr="Some other error",
            )
            assert publisher._is_already_exists_error(result) is False

    def test_publish_runs_build_and_publish(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        space = PythonLibSpace()
        with mock_ctx:
            space.publish(registry="test-pypi", token=None, version="1.0.0")
        captured = capsys.readouterr()
        capture_err = strip_ansi(captured.err)
        assert "uv build" in capture_err
        assert "uv publish" in capture_err

    def test_publish_with_pypi_index(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        space = PythonLibSpace()
        with mock_ctx:
            space.publish(registry="pypi", token=None, version="1.0.0")
        captured = capsys.readouterr()
        capture_err = strip_ansi(captured.err)
        assert "uv build" in capture_err
        assert "uv publish" in capture_err
        assert "--index test-pypi" not in capture_err

    def test_publish_with_test_pypi_index(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        space = PythonLibSpace()
        with mock_ctx:
            space.publish(registry="test-pypi", token=None, version="1.0.0")
        captured = capsys.readouterr()
        capture_err = strip_ansi(captured.err)
        assert "uv build" in capture_err
        assert "uv publish" in capture_err
        assert "--index test-pypi" in capture_err


class TestPublishResult:
    def test_publish_result_fields(self):
        result = PublishResult(
            result=None,
            status=PublishStatus.SUCCESS,
        )
        assert result.result is None
        assert result.status == PublishStatus.SUCCESS
