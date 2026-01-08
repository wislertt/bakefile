from pathlib import Path

from bake.manage.add_inline import read_inline
from bake.ui import run_uv
from bake.utils.constants import CMD_BAKEFILE, DEFAULT_FILE_NAME
from tests.conftest import RunCli


def test_find_python_cli_success_with_inline_metadata(
    empty_project_folder: Path,
    run_cli: RunCli,
) -> None:
    bakefile_path = empty_project_folder / DEFAULT_FILE_NAME
    dummy_test_package = "leetcode-py-sdk"

    # Add inline metadata and dependency
    run_uv(
        ["add", dummy_test_package, "--script", str(bakefile_path.name)], cwd=bakefile_path.parent
    )

    result = run_cli(command=CMD_BAKEFILE, dir_path=empty_project_folder, args=["find-python"])

    python_path = "".join(result.out.splitlines())

    assert result.exit_code == 0
    # The output should be a path to python
    uv_cache_dir_result = run_uv(["cache", "dir"])
    assert uv_cache_dir_result.stdout.strip() in python_path
    assert "python" in python_path


def test_find_python_cli_error_no_bakefile(
    tmp_path: Path,
    run_cli: RunCli,
) -> None:
    result = run_cli(command=CMD_BAKEFILE, dir_path=tmp_path, args=["find-python"])

    assert result.exit_code == 1
    assert "ERROR" in result.err
    assert "Bakefile not found at" in result.err


def test_find_python_cli_success_with_uv_project_with_lock_and_venv(
    uv_project_folder_without_dep: Path,
    run_cli: RunCli,
) -> None:
    dummy_test_package = "leetcode-py-sdk"

    # Add dependency to create lock and venv
    run_uv(["add", dummy_test_package], cwd=uv_project_folder_without_dep)

    result = run_cli(
        command=CMD_BAKEFILE, dir_path=uv_project_folder_without_dep, args=["find-python"]
    )

    assert result.exit_code == 0
    assert ".venv" in result.out
    assert "python" in result.out.lower()


def test_find_python_cli_success_with_uv_project_without_lock_and_venv(
    uv_project_folder_without_dep: Path,
    run_cli: RunCli,
    isolate_virtual_env: None,  # TODO: [Debug]
) -> None:
    _ = isolate_virtual_env
    result = run_cli(
        command=CMD_BAKEFILE, dir_path=uv_project_folder_without_dep, args=["find-python"]
    )

    assert result.exit_code == 0
    assert ".venv" in result.out
    assert "python" in result.out.lower()


def test_find_python_cli_success_with_uv_project_with_lock_without_venv(
    uv_project_folder_without_dep: Path,
    run_cli: RunCli,
) -> None:
    # Create lock but no venv
    run_uv(["lock"], cwd=uv_project_folder_without_dep)

    result = run_cli(
        command=CMD_BAKEFILE, dir_path=uv_project_folder_without_dep, args=["find-python"]
    )

    assert result.exit_code == 0
    assert ".venv" in result.out
    assert "python" in result.out.lower()


def test_find_python_cli_error_no_inline_metadata_no_project(
    empty_project_folder_no_inline: Path,
    run_cli: RunCli,
    isolate_virtual_env: None,
) -> None:
    _ = isolate_virtual_env
    bakefile_path = empty_project_folder_no_inline / DEFAULT_FILE_NAME

    metadata = read_inline(bakefile_path)
    assert metadata is None

    result = run_cli(
        command=CMD_BAKEFILE,
        dir_path=empty_project_folder_no_inline,
        args=["find-python"],
    )

    assert result.exit_code == 1
    assert "ERROR" in result.err
    assert "Could not find Python for" in result.err
