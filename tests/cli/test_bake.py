from typer.testing import CliRunner

from bakefile.cli.bake import app

runner = CliRunner()


def test_bake_hello_world() -> None:
    result = runner.invoke(app)
    assert result.exit_code == 0
    assert result.stdout == "hello world\n"
