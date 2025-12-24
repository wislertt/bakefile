from typer.testing import CliRunner

from bakefile.cli.bakefile import app

runner = CliRunner()


def test_bakefile_hello_world() -> None:
    result = runner.invoke(app)
    assert result.exit_code == 0
    assert result.stdout == "hello world\n"
