import sys
from pathlib import Path

from typer.testing import CliRunner

from bakefile.cli.bake import app
from bakefile.cli.bake import main as main1

runner = CliRunner()


def test_main():
    sys.argv = ["bake"]
    if sys.argv[0].endswith("-script.pyw"):
        sys.argv[0] = sys.argv[0][:-11]
    elif sys.argv[0].endswith(".exe"):
        sys.argv[0] = sys.argv[0][:-4]
    sys.exit(main1())


def test_bake(examples_simple_dir: Path) -> None:
    # With no args, shows main CLI help (same as --help)
    result = runner.invoke(app, ["-C", str(examples_simple_dir)])
    assert result.exit_code == 0
    # Help should show main options
    assert "--chdir" in result.stdout or "-C" in result.stdout
    assert "--file-name" in result.stdout or "-f" in result.stdout
    assert "--book-name" in result.stdout or "-b" in result.stdout


def test_bake__args_help(examples_simple_dir: Path) -> None:
    # With no args, shows main CLI help (same as --help)
    result = runner.invoke(app, ["-C", str(examples_simple_dir), "--help"])
    assert result.exit_code == 0
    # Help should show main options
    assert "--chdir" in result.stdout or "-C" in result.stdout
    assert "--file-name" in result.stdout or "-f" in result.stdout
    assert "--book-name" in result.stdout or "-b" in result.stdout


def test_bake_command_hello(examples_simple_dir: Path) -> None:
    # Can run specific commands
    result = runner.invoke(app, ["-C", str(examples_simple_dir), "hello", "--name", "Claude"])
    assert result.exit_code == 0
    assert "Hello Claude!" in result.stdout


def test_bake_version_option() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout == "0.0.0\n"
