from pathlib import Path

from typer.testing import CliRunner

from bakefile.cli.bake import app

runner = CliRunner()

EXAMPLES_DIR = Path(__file__).parent.parent.parent.parent / "examples" / "simple"


def test_bake_with_chdir() -> None:
    result = runner.invoke(app, ["-C", str(EXAMPLES_DIR)])
    assert result.exit_code == 0
    assert result.stdout == "some_bakebook\n"
