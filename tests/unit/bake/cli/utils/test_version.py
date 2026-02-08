from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from bake.cli.utils.version import _get_version, version_callback

runner = CliRunner()


def test_version_callback_true(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(typer.Exit):
        version_callback(True)
    captured = capsys.readouterr()
    assert captured.out == "0.0.0\n"


def test_version_callback_false(capsys: pytest.CaptureFixture[str]) -> None:
    version_callback(False)
    captured = capsys.readouterr()
    assert captured.out == ""


def test_get_version_returns_fallback_when_package_not_found() -> None:
    """Test that _get_version returns '0.0.0' when PackageNotFoundError is raised."""
    from importlib.metadata import PackageNotFoundError

    with patch("bake.cli.utils.version.version", side_effect=PackageNotFoundError):
        result = _get_version()
        assert result == "0.0.0"
