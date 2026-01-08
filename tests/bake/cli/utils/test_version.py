import pytest
import typer
from typer.testing import CliRunner

from bake.cli.utils.version import version_callback

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
