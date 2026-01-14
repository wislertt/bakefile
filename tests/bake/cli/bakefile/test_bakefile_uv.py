import logging
from pathlib import Path

import orjson

from bake.ui.logger import setup_logging, strip_ansi
from bake.utils.constants import CMD_BAKEFILE
from tests.conftest import RunCli


class TestBakefilePip:
    def inner_test_pip_cli_list(self, run_cli: RunCli, project_folder: Path) -> None:
        setup_logging(level_per_module={"": logging.DEBUG}, is_pretty_log=False)
        result = run_cli(
            command=CMD_BAKEFILE, dir_path=project_folder, args=["pip", "list", "--format=json"]
        )

        assert result.exit_code == 0
        # Check that python version is shown
        assert "Python" in result.err

        packages = orjson.loads(result.out)
        package_names = {package["name"] for package in packages}
        assert "bakefile" in package_names
        assert "pydantic" in package_names
        assert "typer" in package_names

    def test_list_with_inline_metadata(self, empty_project_folder: Path, run_cli: RunCli) -> None:
        self.inner_test_pip_cli_list(run_cli=run_cli, project_folder=empty_project_folder)

    def test_list_with_uv_project(self, uv_project_folder: Path, run_cli: RunCli) -> None:
        self.inner_test_pip_cli_list(run_cli=run_cli, project_folder=uv_project_folder)

    def test_error_no_bakefile(self, tmp_path: Path, run_cli: RunCli) -> None:
        result = run_cli(command=CMD_BAKEFILE, dir_path=tmp_path, args=["pip", "list"])

        assert result.exit_code == 1
        assert "ERROR" in result.err
        assert "Bakefile not found at" in result.err

    def test_invalid_uv_args(self, uv_project_folder: Path, run_cli: RunCli) -> None:
        setup_logging(level_per_module={"": logging.DEBUG}, is_pretty_log=False)
        result = run_cli(
            command=CMD_BAKEFILE, dir_path=uv_project_folder, args=["pip", "list", "--xx"]
        )

        assert result.exit_code == 2
        assert "unexpected argument '--xx' found" in result.err


class TestBakefileAdd:
    def inner_test_add_cli(self, run_cli: RunCli, project_folder: Path) -> None:
        setup_logging(level_per_module={"": logging.DEBUG}, is_pretty_log=False)
        result = run_cli(
            command=CMD_BAKEFILE, dir_path=project_folder, args=["add", "typing-extensions"]
        )

        assert result.exit_code == 0
        assert "Resolved" in result.err
        assert "packages" in result.err

    def test_with_inline_metadata(self, empty_project_folder: Path, run_cli: RunCli) -> None:
        self.inner_test_add_cli(run_cli=run_cli, project_folder=empty_project_folder)

    def test_no_inline_metadata(
        self, empty_project_folder_no_inline: Path, run_cli: RunCli
    ) -> None:
        result = run_cli(
            command=CMD_BAKEFILE, dir_path=empty_project_folder_no_inline, args=["add", "requests"]
        )

        assert result.exit_code == 1
        result_err = strip_ansi(result.err)
        assert "ERROR" in result_err
        assert "requires PEP 723 inline metadata" in result_err
        assert "add-inline" in result_err

    def test_error_no_bakefile(self, tmp_path: Path, run_cli: RunCli) -> None:
        result = run_cli(command=CMD_BAKEFILE, dir_path=tmp_path, args=["add", "requests"])

        assert result.exit_code == 1
        assert "ERROR" in result.err
        assert "Bakefile not found at" in result.err


class TestBakefileLock:
    def inner_test_lock_cli(self, run_cli: RunCli, project_folder: Path) -> None:
        setup_logging(level_per_module={"": logging.DEBUG}, is_pretty_log=False)
        result = run_cli(command=CMD_BAKEFILE, dir_path=project_folder, args=["lock", "--upgrade"])

        assert result.exit_code == 0
        # Check that lock was created
        assert "Resolved" in result.err or "Locked" in result.err

    def test_with_inline_metadata(self, empty_project_folder: Path, run_cli: RunCli) -> None:
        self.inner_test_lock_cli(run_cli=run_cli, project_folder=empty_project_folder)

    def test_no_inline_metadata(
        self, empty_project_folder_no_inline: Path, run_cli: RunCli
    ) -> None:
        result = run_cli(
            command=CMD_BAKEFILE, dir_path=empty_project_folder_no_inline, args=["lock"]
        )

        assert result.exit_code == 1
        result_err = strip_ansi(result.err)
        assert "ERROR" in result_err
        assert "requires PEP 723 inline metadata" in result_err
        assert "add-inline" in result_err

    def test_error_no_bakefile(self, tmp_path: Path, run_cli: RunCli) -> None:
        result = run_cli(command=CMD_BAKEFILE, dir_path=tmp_path, args=["lock"])

        assert result.exit_code == 1
        assert "ERROR" in result.err
        assert "Bakefile not found at" in result.err


class TestBakefileSync:
    def inner_test_sync_cli(self, run_cli: RunCli, project_folder: Path) -> None:
        setup_logging(level_per_module={"": logging.DEBUG}, is_pretty_log=False)
        result = run_cli(
            command=CMD_BAKEFILE, dir_path=project_folder, args=["sync", "--upgrade", "--reinstall"]
        )

        assert result.exit_code == 0
        # Check that sync was successful
        assert "Resolved" in result.err
        assert "packages" in result.err

    def test_with_inline_metadata(self, empty_project_folder: Path, run_cli: RunCli) -> None:
        self.inner_test_sync_cli(run_cli=run_cli, project_folder=empty_project_folder)

    def test_no_inline_metadata(
        self, empty_project_folder_no_inline: Path, run_cli: RunCli
    ) -> None:
        result = run_cli(
            command=CMD_BAKEFILE, dir_path=empty_project_folder_no_inline, args=["sync"]
        )

        assert result.exit_code == 1
        result_err = strip_ansi(result.err)
        assert "ERROR" in result_err
        assert "requires PEP 723 inline metadata" in result_err
        assert "add-inline" in result_err

    def test_error_no_bakefile(self, tmp_path: Path, run_cli: RunCli) -> None:
        result = run_cli(command=CMD_BAKEFILE, dir_path=tmp_path, args=["sync"])

        assert result.exit_code == 1
        assert "ERROR" in result.err
        assert "Bakefile not found at" in result.err
