import subprocess

import pytest

from bake import Context
from bake.ui.logger import strip_ansi
from bakelib.space.lib import PublishResult
from bakelib.space.python_lib import PythonLibSpace


class TestPythonLibSpace:
    def test_version_schema_returns_standard_base_prerelease_post_dev(self):
        space = PythonLibSpace()
        assert space._version_schema == "standard-base-prerelease-post-dev"

    def test_version_output_format_returns_pep440(self):
        space = PythonLibSpace()
        assert space._version_output_format == "pep440"

    def test_registry_to_index_returns_valid_indices(self):
        space = PythonLibSpace()
        assert space._registry_to_index("testpypi") == "testpypi"
        assert space._registry_to_index("pypi") == "pypi"

    def test_registry_to_index_raises_error_for_invalid_registry(self):
        space = PythonLibSpace()
        with pytest.raises(ValueError, match="Invalid registry"):
            space._registry_to_index("invalid")

    def test_get_publish_token_from_remote_returns_none(self):
        space = PythonLibSpace()
        token = space._get_publish_token_from_remote("testpypi")
        assert token is None

    def test_is_auth_failure_detects_403_error(self):
        space = PythonLibSpace()
        result = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stderr="403 Invalid or non-existent authentication information",
        )
        assert space._is_auth_failure(result) is True

    def test_is_auth_failure_returns_false_for_non_403_errors(self):
        space = PythonLibSpace()
        result = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stderr="Some other error",
        )
        assert space._is_auth_failure(result) is False

    def test_is_auth_failure_returns_false_for_success(self):
        space = PythonLibSpace()
        result = subprocess.CompletedProcess(args=[], returncode=0, stderr="")
        assert space._is_auth_failure(result) is False

    def test_publish_runs_build_and_publish(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        space = PythonLibSpace()
        space.publish(mock_ctx, index="testpypi", token=None, version="1.0.0")
        captured = capsys.readouterr()
        capture_err = strip_ansi(captured.err)
        assert "uv build" in capture_err
        assert "uv publish" in capture_err

    def test_publish_with_pypi_index(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        space = PythonLibSpace()
        space.publish(mock_ctx, index="pypi", token=None, version="1.0.0")
        captured = capsys.readouterr()
        capture_err = strip_ansi(captured.err)
        assert "uv build" in capture_err
        assert "uv publish" in capture_err
        assert "--index testpypi" not in capture_err

    def test_publish_with_testpypi_index(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        space = PythonLibSpace()
        space.publish(mock_ctx, index="testpypi", token=None, version="1.0.0")
        captured = capsys.readouterr()
        capture_err = strip_ansi(captured.err)
        assert "uv build" in capture_err
        assert "uv publish" in capture_err
        assert "--index testpypi" in capture_err


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
