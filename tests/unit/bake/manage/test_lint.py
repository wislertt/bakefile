from pathlib import Path

import pytest

from bake.manage.find_python import find_python_path
from bake.manage.lint import run_ruff_check, run_ruff_format, run_ty_check
from bake.ui.logger import strip_ansi
from bake.utils.constants import DEFAULT_FILE_NAME


class TestRunRuffFormat:
    def inner_test_ruff_format(
        self, project_folder: Path, only_bakefile: bool, expected_msg: str
    ) -> None:
        bakefile_path = project_folder / DEFAULT_FILE_NAME

        result = run_ruff_format(
            bakefile_path, only_bakefile=only_bakefile, check=False, dry_run=False
        )

        assert result.returncode == 0
        assert result.stdout is not None
        assert result.stdout.strip() == expected_msg

    @pytest.mark.parametrize("only_bakefile", [False, True])
    def test_empty_project(self, empty_project_folder: Path, only_bakefile: bool) -> None:
        self.inner_test_ruff_format(empty_project_folder, only_bakefile, "1 file left unchanged")

    @pytest.mark.parametrize(
        "only_bakefile,expected",
        [(False, "3 files left unchanged"), (True, "1 file left unchanged")],
    )
    def test_uv_project(self, uv_project_folder: Path, only_bakefile: bool, expected: str) -> None:
        self.inner_test_ruff_format(uv_project_folder, only_bakefile, expected)


class TestRunRuffCheck:
    def inner_test_ruff_check(self, project_folder: Path, only_bakefile: bool) -> None:
        bakefile_path = project_folder / DEFAULT_FILE_NAME

        result = run_ruff_check(
            bakefile_path, only_bakefile=only_bakefile, check=False, dry_run=False
        )

        assert result.returncode in {0, 1}
        assert result.stdout is not None
        assert (
            "Found" in result.stdout.strip() and "error" in result.stdout.strip()
        ) or "All checks passed!" in result.stdout.strip()

    @pytest.mark.parametrize("only_bakefile", [False, True])
    def test_empty_project(self, empty_project_folder: Path, only_bakefile: bool) -> None:
        self.inner_test_ruff_check(empty_project_folder, only_bakefile)

    @pytest.mark.parametrize("only_bakefile", [False, True])
    def test_uv_project(self, uv_project_folder: Path, only_bakefile: bool) -> None:
        self.inner_test_ruff_check(uv_project_folder, only_bakefile)


class TestRunTyCheck:
    def inner_test_ty_check(self, project_folder: Path, only_bakefile: bool) -> None:
        bakefile_path = project_folder / DEFAULT_FILE_NAME
        python_path = find_python_path(bakefile_path)

        result = run_ty_check(
            bakefile_path, python_path, only_bakefile=only_bakefile, check=False, dry_run=False
        )

        assert result.returncode == 0
        assert result.stdout is not None
        assert strip_ansi(result.stdout).strip() == "All checks passed!"

    @pytest.mark.parametrize("only_bakefile", [False, True])
    def test_empty_project(self, empty_project_folder: Path, only_bakefile: bool) -> None:
        self.inner_test_ty_check(empty_project_folder, only_bakefile)

    @pytest.mark.parametrize("only_bakefile", [False, True])
    def test_uv_project(self, uv_project_folder: Path, only_bakefile: bool) -> None:
        self.inner_test_ty_check(uv_project_folder, only_bakefile)
