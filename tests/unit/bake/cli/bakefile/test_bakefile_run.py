from pathlib import Path

from bake.utils.constants import CMD_BAKEFILE
from tests.conftest import RunCli
from tests.utils.cli import get_error_label


def test_run_help_shows_help(tmp_path: Path, run_cli: RunCli) -> None:
    result = run_cli(command=CMD_BAKEFILE, dir_path=tmp_path, args=["run", "--help"])

    assert result.exit_code == 0
    assert "python <args>" in result.out
    assert "bakefile's Python environment" in result.out


def test_run_module_with_inline_metadata(empty_project_folder: Path, run_cli: RunCli) -> None:
    # Create a simple test script that we can run as a module
    test_script = empty_project_folder / "test_module.py"
    test_script.write_text("print('hello from module')")

    result = run_cli(
        command=CMD_BAKEFILE, dir_path=empty_project_folder, args=["run", "test_module"]
    )

    assert result.exit_code == 0
    assert "hello from module" in result.out


def test_run_script_file_with_inline_metadata(empty_project_folder: Path, run_cli: RunCli) -> None:
    # Create a simple test script
    test_script = empty_project_folder / "test_script.py"
    test_script.write_text("print('hello from script')")

    result = run_cli(
        command=CMD_BAKEFILE, dir_path=empty_project_folder, args=["run", "test_script.py"]
    )

    assert result.exit_code == 0
    assert "hello from script" in result.out
    # Check that the echo shows the script name as typed, not full path
    assert "python test_script.py" in result.err


def test_run_error_no_bakefile(tmp_path: Path, run_cli: RunCli) -> None:
    result = run_cli(command=CMD_BAKEFILE, dir_path=tmp_path, args=["run", "pytest"])

    assert result.exit_code == 1
    assert get_error_label() in result.err
    assert "Bakefile not found at" in result.err


def test_run_with_args(empty_project_folder: Path, run_cli: RunCli) -> None:
    # Create a test script that prints sys.argv
    test_script = empty_project_folder / "test_args.py"
    test_script.write_text("import sys; print(' '.join(sys.argv[1:]))")

    result = run_cli(
        command=CMD_BAKEFILE,
        dir_path=empty_project_folder,
        args=["run", "test_args.py", "arg1", "arg2"],
    )

    assert result.exit_code == 0
    assert "arg1 arg2" in result.out


def test_run_script_fails_with_non_zero_exit(empty_project_folder: Path, run_cli: RunCli) -> None:
    # Create a test script that exits with error
    test_script = empty_project_folder / "test_fail.py"
    test_script.write_text("import sys; sys.exit(42)")

    result = run_cli(
        command=CMD_BAKEFILE, dir_path=empty_project_folder, args=["run", "test_fail.py"]
    )

    assert result.exit_code == 42
