import logging
from pathlib import Path

import orjson
import pytest

from bake.manage.run_uv import run_uv_add, run_uv_lock, run_uv_pip, run_uv_sync
from bake.ui.logger import setup_logging
from bake.utils import BakebookError
from bake.utils.constants import DEFAULT_FILE_NAME
from bake.utils.exceptions import PythonNotFoundError


class TestRunUvAdd:
    def inner_test_run_uv_add(self, project_folder: Path):
        setup_logging(level_per_module={"": logging.DEBUG}, is_pretty_log=False)
        bakefile_path = project_folder / DEFAULT_FILE_NAME

        result = run_uv_add(bakefile_path, ["typing-extensions"], dry_run=False)

        assert result.returncode == 0
        assert result.stdout is not None
        assert result.stderr is not None
        assert "Resolved" in result.stderr
        assert "packages in" in result.stderr

    def test_with_inline_metadata(self, empty_project_folder: Path) -> None:
        self.inner_test_run_uv_add(project_folder=empty_project_folder)

    def test_no_inline_metadata(self, empty_project_folder_no_inline: Path) -> None:
        bakefile_path = empty_project_folder_no_inline / DEFAULT_FILE_NAME

        with pytest.raises(BakebookError) as exc_info:
            run_uv_add(bakefile_path, ["typing-extensions"], dry_run=False)

        assert "requires PEP 723 inline metadata" in str(exc_info.value)
        assert "add-inline" in str(exc_info.value)

    def test_bakefile_not_found(self, empty_project_folder: Path) -> None:
        fake_path = empty_project_folder / "nonexistent.py"

        with pytest.raises(PythonNotFoundError) as exc_info:
            run_uv_add(fake_path, ["typing-extensions"], dry_run=False)

        assert "Bakefile not found" in str(exc_info.value)


class TestRunUvLock:
    def inner_test_run_uv_lock(self, project_folder: Path):
        setup_logging(level_per_module={"": logging.DEBUG}, is_pretty_log=False)
        bakefile_path = project_folder / DEFAULT_FILE_NAME

        result = run_uv_lock(bakefile_path, [], dry_run=False)

        assert result.returncode == 0
        assert result.stdout is not None

    def test_with_inline_metadata(self, empty_project_folder: Path) -> None:
        self.inner_test_run_uv_lock(project_folder=empty_project_folder)

    def test_no_inline_metadata(self, empty_project_folder_no_inline: Path) -> None:
        bakefile_path = empty_project_folder_no_inline / DEFAULT_FILE_NAME

        with pytest.raises(BakebookError) as exc_info:
            run_uv_lock(bakefile_path, [], dry_run=False)

        assert "requires PEP 723 inline metadata" in str(exc_info.value)
        assert "add-inline" in str(exc_info.value)

    def test_bakefile_not_found(self, empty_project_folder: Path) -> None:
        fake_path = empty_project_folder / "nonexistent.py"

        with pytest.raises(PythonNotFoundError) as exc_info:
            run_uv_lock(fake_path, [], dry_run=False)

        assert "Bakefile not found" in str(exc_info.value)


class TestRunUvSync:
    def inner_test_run_uv_sync(self, project_folder: Path):
        setup_logging(level_per_module={"": logging.DEBUG}, is_pretty_log=False)
        bakefile_path = project_folder / DEFAULT_FILE_NAME

        result = run_uv_sync(bakefile_path, [], dry_run=False)

        assert result.returncode == 0
        assert result.stdout is not None

    def test_with_inline_metadata(self, empty_project_folder: Path) -> None:
        self.inner_test_run_uv_sync(project_folder=empty_project_folder)

    def test_no_inline_metadata(self, empty_project_folder_no_inline: Path) -> None:
        bakefile_path = empty_project_folder_no_inline / DEFAULT_FILE_NAME

        with pytest.raises(BakebookError) as exc_info:
            run_uv_sync(bakefile_path, [], dry_run=False)

        assert "requires PEP 723 inline metadata" in str(exc_info.value)
        assert "add-inline" in str(exc_info.value)

    def test_bakefile_not_found(self, empty_project_folder: Path) -> None:
        fake_path = empty_project_folder / "nonexistent.py"

        with pytest.raises(PythonNotFoundError) as exc_info:
            run_uv_sync(fake_path, [], dry_run=False)

        assert "Bakefile not found" in str(exc_info.value)

    def test_dry_run(self, empty_project_folder: Path, capfd: pytest.CaptureFixture[str]) -> None:
        bakefile_path = empty_project_folder / DEFAULT_FILE_NAME

        result = run_uv_sync(bakefile_path, [], dry_run=True)

        # Dry run should return success without executing
        assert result.returncode == 0
        assert result.stdout == ""

        # Check that the command was printed (from run_uv's echo=True)
        captured = capfd.readouterr()
        assert "uv sync" in captured.err


class TestRunUvPip:
    def inner_test_run_uv_pip(self, project_folder: Path):
        setup_logging(level_per_module={"": logging.DEBUG}, is_pretty_log=False)
        bakefile_path = project_folder / DEFAULT_FILE_NAME

        result = run_uv_pip(bakefile_path, ["list", "--format=json"], dry_run=False)

        assert isinstance(result.stdout, str)

        packages = orjson.loads(result.stdout)
        package_names = {package["name"] for package in packages}
        assert "bakefile" in package_names
        assert "pydantic" in package_names
        assert "typer" in package_names

    def test_with_inline_metadata(self, empty_project_folder: Path) -> None:
        self.inner_test_run_uv_pip(project_folder=empty_project_folder)

    def test_with_uv_project(self, uv_project_folder: Path) -> None:
        self.inner_test_run_uv_pip(project_folder=uv_project_folder)
