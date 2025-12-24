from pathlib import Path

from typer.testing import CliRunner

from bakefile.cli.bake import app

runner = CliRunner()


def test_bake_with_chdir(examples_simple_dir: Path) -> None:
    result = runner.invoke(app, ["-C", str(examples_simple_dir)])
    assert result.exit_code == 0
    assert result.stdout == "some_bakebook\n"


def test_bake_version_option() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout == "0.0.0\n"
