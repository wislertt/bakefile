from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from bake.cli.utils.version import (
    _colorize_version_string,
    _format_version,
    _get_version,
    _parse_version_string,
    make_version_callback,
)

runner = CliRunner()


def test_make_version_callback_bake_label(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(typer.Exit):
        make_version_callback("bake")(True)
    out = capsys.readouterr().out
    assert out.startswith("bake ")
    assert " from " in out
    assert "(python " in out
    assert out.endswith(")\n")


def test_make_version_callback_bakefile_label(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(typer.Exit):
        make_version_callback("bakefile")(True)
    out = capsys.readouterr().out
    assert out.startswith("bakefile ")
    assert " from " in out
    assert "(python " in out


def test_make_version_callback_false_no_output(capsys: pytest.CaptureFixture[str]) -> None:
    make_version_callback("bake")(False)
    captured = capsys.readouterr()
    assert captured.out == ""


def test_get_version_returns_fallback_when_package_not_found() -> None:
    """Test that _get_version returns '0.0.0' when PackageNotFoundError is raised."""
    from importlib.metadata import PackageNotFoundError

    with patch("bake.cli.utils.version.version", side_effect=PackageNotFoundError):
        result = _get_version()
        assert result == "0.0.0"


def test_format_version_contains_all_components() -> None:
    line = _format_version("bake")
    assert line.startswith("bake ")
    assert " from " in line
    assert "(python " in line


def test_parse_version_string_extracts_components() -> None:
    raw = "bakefile 0.0.54 from /venv/lib/bake (python 3.12.1)"
    parts = _parse_version_string(raw)
    assert parts is not None
    assert parts["label"] == "bakefile"
    assert parts["version"] == "0.0.54"
    assert parts["path"] == "/venv/lib/bake"
    assert parts["pyver"] == "3.12.1"


def test_parse_version_string_handles_path_with_spaces() -> None:
    raw = "bake 1.2.3 from /Users/Some One/bake (python 3.13.0)"
    parts = _parse_version_string(raw)
    assert parts is not None
    assert parts["path"] == "/Users/Some One/bake"
    assert parts["pyver"] == "3.13.0"


def test_parse_version_string_none_on_malformed() -> None:
    assert _parse_version_string("not a version line") is None
    assert _parse_version_string("") is None


def test_colorize_version_string_returns_text() -> None:
    text = _colorize_version_string("bakefile 0.0.54 from /venv (python 3.12.1)")
    assert text is not None
    rendered = text.plain
    assert rendered == "bakefile 0.0.54 from /venv (python 3.12.1)"


def test_colorize_version_string_none_on_malformed() -> None:
    assert _colorize_version_string("garbage") is None
