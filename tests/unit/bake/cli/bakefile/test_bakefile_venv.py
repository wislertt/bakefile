from pathlib import Path

from bake.ui import run_uv
from bake.utils.constants import CMD_BAKEFILE, DEFAULT_FILE_NAME
from bake.utils.exceptions import PythonNotFoundError
from tests.conftest import RunCli
from tests.utils.cli import get_error_label


def test_venv_creates_symlink_for_pep723(
    empty_project_folder: Path,
    run_cli: RunCli,
) -> None:
    bakefile_path = empty_project_folder / DEFAULT_FILE_NAME
    dummy_test_package = "leetcode-py-sdk"
    run_uv(
        ["add", dummy_test_package, "--script", str(bakefile_path.name)], cwd=bakefile_path.parent
    )

    result = run_cli(command=CMD_BAKEFILE, dir_path=empty_project_folder, args=["venv"])

    venv_path = empty_project_folder / ".venv"
    assert result.exit_code == 0
    assert venv_path.is_symlink()
    assert "Linked .venv ->" in result.err


def test_venv_fails_when_venv_directory_exists(
    empty_project_folder: Path,
    run_cli: RunCli,
) -> None:
    bakefile_path = empty_project_folder / DEFAULT_FILE_NAME
    dummy_test_package = "leetcode-py-sdk"
    run_uv(
        ["add", dummy_test_package, "--script", str(bakefile_path.name)], cwd=bakefile_path.parent
    )

    # Create a real .venv directory
    venv_path = empty_project_folder / ".venv"
    venv_path.mkdir()

    result = run_cli(command=CMD_BAKEFILE, dir_path=empty_project_folder, args=["venv"])

    assert result.exit_code == 1
    assert get_error_label() in result.err
    assert "already exists (directory)" in result.err


def test_venv_fails_when_symlink_exists_without_force(
    empty_project_folder: Path,
    run_cli: RunCli,
) -> None:
    bakefile_path = empty_project_folder / DEFAULT_FILE_NAME
    dummy_test_package = "leetcode-py-sdk"
    run_uv(
        ["add", dummy_test_package, "--script", str(bakefile_path.name)], cwd=bakefile_path.parent
    )

    # Create symlink first
    run_cli(command=CMD_BAKEFILE, dir_path=empty_project_folder, args=["venv"])

    result = run_cli(command=CMD_BAKEFILE, dir_path=empty_project_folder, args=["venv"])

    assert result.exit_code == 1
    assert get_error_label() in result.err
    assert "already exists (symlink" in result.err


def test_venv_force_overwrites_symlink(
    empty_project_folder: Path,
    run_cli: RunCli,
) -> None:
    bakefile_path = empty_project_folder / DEFAULT_FILE_NAME
    dummy_test_package = "leetcode-py-sdk"
    run_uv(
        ["add", dummy_test_package, "--script", str(bakefile_path.name)], cwd=bakefile_path.parent
    )

    # Create symlink first
    run_cli(command=CMD_BAKEFILE, dir_path=empty_project_folder, args=["venv"])
    venv_path = empty_project_folder / ".venv"
    assert venv_path.is_symlink()

    result = run_cli(command=CMD_BAKEFILE, dir_path=empty_project_folder, args=["venv", "--force"])

    assert result.exit_code == 0
    assert venv_path.is_symlink()
    assert "Linked .venv ->" in result.err


def test_venv_force_does_not_remove_real_directory(
    empty_project_folder: Path,
    run_cli: RunCli,
) -> None:
    bakefile_path = empty_project_folder / DEFAULT_FILE_NAME
    dummy_test_package = "leetcode-py-sdk"
    run_uv(
        ["add", dummy_test_package, "--script", str(bakefile_path.name)], cwd=bakefile_path.parent
    )

    venv_path = empty_project_folder / ".venv"
    venv_path.mkdir()

    result = run_cli(command=CMD_BAKEFILE, dir_path=empty_project_folder, args=["venv", "--force"])

    assert result.exit_code == 1
    assert get_error_label() in result.err
    assert "already exists (directory)" in result.err


def test_venv_runs_sync_for_pyproject(
    uv_project_folder_without_dep: Path,
    run_cli: RunCli,
    isolate_virtual_env: None,
) -> None:
    _ = isolate_virtual_env
    result = run_cli(command=CMD_BAKEFILE, dir_path=uv_project_folder_without_dep, args=["venv"])

    venv_path = uv_project_folder_without_dep / ".venv"
    assert result.exit_code == 0
    assert venv_path.exists()
    assert ".venv created at" in result.err


def test_venv_fails_when_no_bakefile(
    tmp_path: Path,
    run_cli: RunCli,
) -> None:
    result = run_cli(command=CMD_BAKEFILE, dir_path=tmp_path, args=["venv"])

    assert result.exit_code == 1
    assert get_error_label() in result.err
    assert "Bakefile not found" in result.err


def test_venv_fails_when_python_not_found(
    empty_project_folder: Path,
    run_cli: RunCli,
    isolate_virtual_env: None,
) -> None:
    _ = isolate_virtual_env
    from unittest.mock import patch

    with patch(
        "bake.cli.bakefile.venv.find_python_path", side_effect=PythonNotFoundError("no python")
    ):
        result = run_cli(command=CMD_BAKEFILE, dir_path=empty_project_folder, args=["venv"])

    assert result.exit_code == 1
    assert get_error_label() in result.err
    assert "no python" in result.err
