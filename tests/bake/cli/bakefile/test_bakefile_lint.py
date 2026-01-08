from pathlib import Path

import pytest

from bake.utils.constants import CMD_BAKEFILE, CMD_LINT
from tests.conftest import RunCli


@pytest.mark.integration
def test_lint_default_runs_all_linters(empty_project_folder: Path, run_cli: RunCli) -> None:
    result = run_cli(
        command=CMD_BAKEFILE, dir_path=empty_project_folder, args=["--dry-run", CMD_LINT]
    )
    assert result.exit_code == 0
    assert "ruff format" in result.err
    assert "ruff check" in result.err
    assert "ty check" in result.err


@pytest.mark.integration
def test_lint_only_bakefile(empty_project_folder: Path, run_cli: RunCli) -> None:
    result = run_cli(
        command=CMD_BAKEFILE, dir_path=empty_project_folder, args=["--dry-run", CMD_LINT, "-b"]
    )
    assert result.exit_code == 0
    assert "ruff format" in result.err
    assert "ruff check" in result.err
    assert "ty check" in result.err


@pytest.mark.integration
def test_lint_no_ruff_format(empty_project_folder: Path, run_cli: RunCli) -> None:
    result = run_cli(
        command=CMD_BAKEFILE,
        dir_path=empty_project_folder,
        args=["--dry-run", CMD_LINT, "--no-ruff-format"],
    )
    assert result.exit_code == 0
    assert "ruff format" not in result.err
    assert "ruff check" in result.err
    assert "ty check" in result.err


@pytest.mark.integration
def test_lint_no_ruff_check(empty_project_folder: Path, run_cli: RunCli) -> None:
    result = run_cli(
        command=CMD_BAKEFILE,
        dir_path=empty_project_folder,
        args=["--dry-run", CMD_LINT, "--no-ruff-check"],
    )
    assert result.exit_code == 0
    assert "ruff format" in result.err
    assert "ruff check" not in result.err
    assert "ty check" in result.err


@pytest.mark.integration
def test_lint_no_ty(empty_project_folder: Path, run_cli: RunCli) -> None:
    result = run_cli(
        command=CMD_BAKEFILE, dir_path=empty_project_folder, args=["--dry-run", CMD_LINT, "--no-ty"]
    )
    assert result.exit_code == 0
    assert "ruff format" in result.err
    assert "ruff check" in result.err
    assert "ty check" not in result.err


@pytest.mark.integration
def test_lint_combined_flags(empty_project_folder: Path, run_cli: RunCli) -> None:
    result = run_cli(
        command=CMD_BAKEFILE,
        dir_path=empty_project_folder,
        args=["--dry-run", CMD_LINT, "-b", "--no-ty"],
    )
    assert result.exit_code == 0
    assert "ruff format" in result.err
    assert "ruff check" in result.err
    assert "ty check" not in result.err


@pytest.mark.integration
def test_lint_all_linters_disabled(empty_project_folder: Path, run_cli: RunCli) -> None:
    result = run_cli(
        command=CMD_BAKEFILE,
        dir_path=empty_project_folder,
        args=["--dry-run", CMD_LINT, "--no-ruff-format", "--no-ruff-check", "--no-ty"],
    )

    assert result.exit_code == 0
    assert "All linters disabled" in result.err


@pytest.mark.integration
def test_lint_no_bakefile(tmp_path: Path, run_cli: RunCli) -> None:
    result = run_cli(command=CMD_BAKEFILE, dir_path=tmp_path, args=[CMD_LINT])

    assert result.exit_code == 1
    assert "Bakefile not found" in result.err
