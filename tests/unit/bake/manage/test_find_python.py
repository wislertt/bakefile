import logging
import re
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bake.manage.find_python import _find_project_python, find_python_path
from bake.ui import run_uv
from bake.ui.logger import (
    capsys_to_logs,
    count_message_in_logs,
    has_messages_in_logs,
    setup_logging,
)
from bake.utils import BakebookError
from bake.utils.constants import DEFAULT_FILE_NAME
from bake.utils.exceptions import PythonNotFoundError


def assert_bakefile_level_python_exe(python_path: Path):
    assert python_path.exists()
    result = run_uv(["cache", "dir"])
    assert result.stdout.strip() in str(python_path)
    assert "python" in python_path.name.lower()
    return True


def assert_project_level_python_exe(python_path: Path, project_folder: Path):
    assert python_path.exists()
    assert ".venv" in python_path.as_posix()
    assert "python" in python_path.name.lower()
    assert python_path.as_posix().startswith(project_folder.as_posix())
    return True


def test_find_python_with_inline_metadata_without_lock_and_venv(
    empty_project_folder: Path,
    capfd: pytest.CaptureFixture[str],
) -> None:
    """Case: bakefile.py with inline metadata, no lock, no venv.

    If this test fails locally, try `uv cache clean` first.
    """
    # Arrange ================
    setup_logging(
        level_per_module={"": logging.DEBUG},
        is_pretty_log=False,
    )
    bakefile_path = empty_project_folder / DEFAULT_FILE_NAME
    dummy_test_package = "leetcode-py-sdk"
    # Add inline metadata and dependency (no lock, no venv yet)
    run_uv(
        ["add", dummy_test_package, "--script", str(bakefile_path.name)], cwd=bakefile_path.parent
    )

    # Act ====================
    _ = capfd.readouterr()
    python_path = find_python_path(bakefile_path)

    # Assert =================
    logs = capsys_to_logs(capfd)
    assert count_message_in_logs(logs, message=r"\[run\].*uv") == 4
    assert has_messages_in_logs(
        logs,
        [
            "Bakefile has inline metadata -> bakefile-level Python",
            "No bakefile Python found",
            "No bakefile lock found",
            "Creating bakefile lock and syncing",
            "Found bakefile Python at",
        ],
    )
    assert assert_bakefile_level_python_exe(python_path)

    result = run_uv(["pip", "list", "--python", str(python_path)])
    assert isinstance(result.stdout, str)
    assert dummy_test_package in result.stdout


def test_find_python_with_inline_metadata_with_lock_and_venv(
    empty_project_folder: Path,
    capfd: pytest.CaptureFixture[str],
) -> None:
    """Case: bakefile.py with inline metadata, with lock and venv already set up."""
    # Arrange ================
    setup_logging(
        level_per_module={"": logging.DEBUG},
        is_pretty_log=False,
    )
    bakefile_path = empty_project_folder / DEFAULT_FILE_NAME
    dummy_test_package = "leetcode-py-sdk"
    # Add inline metadata and dependency
    run_uv(
        ["add", dummy_test_package, "--script", str(bakefile_path.name)], cwd=bakefile_path.parent
    )
    # Explicitly set up lock and venv (simulating pre-existing environment)
    run_uv(["lock", "--script", str(bakefile_path.name)], check=True, cwd=bakefile_path.parent)
    run_uv(["sync", "--script", str(bakefile_path.name)], check=True, cwd=bakefile_path.parent)

    # Act ====================
    _ = capfd.readouterr()
    python_path = find_python_path(bakefile_path)

    # Assert =================
    logs = capsys_to_logs(capfd)
    assert count_message_in_logs(logs, message=r"\[run\].*uv") == 1
    assert has_messages_in_logs(
        logs,
        [
            "Bakefile has inline metadata -> bakefile-level Python",
            "Found bakefile Python at",
        ],
    )
    assert assert_bakefile_level_python_exe(python_path)


def test_find_python_with_inline_metadata_with_lock_without_venv(
    empty_project_folder: Path,
    capfd: pytest.CaptureFixture[str],
) -> None:
    """Case: bakefile.py with inline metadata, with lock but no venv.

    If this test fails locally, try `uv cache clean` first.
    """
    # Arrange ================
    setup_logging(
        level_per_module={"": logging.DEBUG},
        is_pretty_log=False,
    )
    bakefile_path = empty_project_folder / DEFAULT_FILE_NAME
    run_uv(["lock", "--script", str(bakefile_path.name)], cwd=bakefile_path.parent)

    # Act ====================
    _ = capfd.readouterr()
    python_path = find_python_path(bakefile_path)

    # Assert =================
    logs = capsys_to_logs(capfd)
    assert count_message_in_logs(logs, message=r"\[run\].*uv") == 3
    assert has_messages_in_logs(
        logs,
        [
            "Bakefile has inline metadata -> bakefile-level Python",
            "No bakefile Python found",
            "Found bakefile lock",
            "Syncing bakefile with frozen lock",
            "Found bakefile Python at",
        ],
    )
    assert assert_bakefile_level_python_exe(python_path)


def test_find_python_with_uv_project_with_lock_and_venv(
    uv_project_folder_without_dep: Path,
    capfd: pytest.CaptureFixture[str],
    isolate_virtual_env: None,
) -> None:
    """Case: uv project with lock and venv already set up."""
    _ = isolate_virtual_env
    # Arrange ================
    setup_logging(
        level_per_module={"": logging.DEBUG},
        is_pretty_log=False,
    )
    bakefile_path = uv_project_folder_without_dep / DEFAULT_FILE_NAME
    dummy_test_package = "leetcode-py-sdk"
    run_uv(["add", dummy_test_package], cwd=uv_project_folder_without_dep)

    # Act ====================
    _ = capfd.readouterr()
    python_path = find_python_path(bakefile_path)

    # Assert =================
    logs = capsys_to_logs(capfd)
    assert count_message_in_logs(logs, message=r"\[run\].*uv") == 1
    assert has_messages_in_logs(
        logs,
        [
            "No inline metadata -> project-level Python",
            re.escape(f"Found project Python at {python_path} (source: virtual environment)"),
        ],
    )
    assert assert_project_level_python_exe(python_path, uv_project_folder_without_dep)
    result = run_uv(["pip", "list"], cwd=uv_project_folder_without_dep)
    assert isinstance(result.stdout, str)
    assert dummy_test_package in result.stdout


def test_find_python_with_uv_project_without_lock_and_venv(
    uv_project_folder_without_dep: Path,
    capfd: pytest.CaptureFixture[str],
    isolate_virtual_env: None,
) -> None:
    """Case: uv project without lock and venv."""
    # Arrange ================
    _ = isolate_virtual_env
    setup_logging(
        level_per_module={"": logging.DEBUG},
        is_pretty_log=False,
    )
    bakefile_path = uv_project_folder_without_dep / DEFAULT_FILE_NAME

    # Act ====================
    _ = capfd.readouterr()
    python_path = find_python_path(bakefile_path)

    # Assert =================
    logs = capsys_to_logs(capfd)
    assert count_message_in_logs(logs, message=r"\[run\].*uv") == 4
    assert has_messages_in_logs(
        logs,
        [
            "No inline metadata -> project-level Python",
            "No project Python found",
            "No project lock found",
            "Creating project lock and syncing",
            re.escape(f"Found project Python at {python_path} (source: virtual environment)"),
        ],
    )
    assert assert_project_level_python_exe(python_path, uv_project_folder_without_dep)


def test_find_python_with_uv_project_with_lock_without_venv(
    uv_project_folder_without_dep: Path,
    capfd: pytest.CaptureFixture[str],
    isolate_virtual_env: None,
) -> None:
    """Case: uv project with lock but no venv."""
    _ = isolate_virtual_env
    # Arrange ================
    setup_logging(
        level_per_module={"": logging.DEBUG},
        is_pretty_log=False,
    )
    bakefile_path = uv_project_folder_without_dep / DEFAULT_FILE_NAME
    run_uv(["lock"], cwd=uv_project_folder_without_dep)

    # Act ====================
    _ = capfd.readouterr()
    python_path = find_python_path(bakefile_path)

    # Assert =================
    logs = capsys_to_logs(capfd)
    assert count_message_in_logs(logs, message=r"\[run\].*uv") == 3
    assert has_messages_in_logs(
        logs,
        [
            "No inline metadata -> project-level Python",
            "No project Python found",
            "Found project lock at",
            "Syncing project with frozen lock",
            re.escape(f"Found project Python at {python_path} (source: virtual environment)"),
        ],
    )
    assert assert_project_level_python_exe(python_path, uv_project_folder_without_dep)


def test_find_python_with_empty_project_no_inline_metadata(
    empty_project_folder_no_inline: Path,
    capfd: pytest.CaptureFixture[str],
    isolate_virtual_env: None,
) -> None:
    """Case: empty project without inline metadata and no pyproject.toml - should raise error."""
    _ = isolate_virtual_env
    # Arrange ================
    setup_logging(
        level_per_module={"": logging.DEBUG},
        is_pretty_log=False,
    )
    bakefile_path = empty_project_folder_no_inline / DEFAULT_FILE_NAME

    # Act ====================
    _ = capfd.readouterr()
    with pytest.raises(PythonNotFoundError) as exc_info:
        find_python_path(bakefile_path)

    # Assert =================
    logs = capsys_to_logs(capfd)
    assert has_messages_in_logs(
        logs,
        [
            "No inline metadata -> project-level Python",
            "No project Python found",
            "No pyproject.toml found, cannot create project venv",
        ],
    )
    error_message = str(exc_info.value)
    assert "Could not find Python for" in error_message
    assert str(bakefile_path) in error_message
    assert (
        "Run 'bakefile add-inline' to add PEP 723 metadata for bakefile-level Python."
        in error_message
    )


def test_find_python_with_invalid_inline(
    empty_project_folder_no_inline: Path,
    capfd: pytest.CaptureFixture[str],
    isolate_virtual_env: None,
) -> None:
    """Case: inline metadata exists but missing 'bakefile' dependency."""
    # Arrange ================
    _ = isolate_virtual_env
    setup_logging(
        level_per_module={"": logging.DEBUG},
        is_pretty_log=False,
    )
    bakefile_path = empty_project_folder_no_inline / DEFAULT_FILE_NAME
    run_uv(["init", "--script", str(bakefile_path.name)], cwd=empty_project_folder_no_inline)

    # Act ====================
    _ = capfd.readouterr()
    with pytest.raises(BakebookError) as exc_info:
        find_python_path(bakefile_path)

    # Assert =================
    error_message = str(exc_info.value)
    assert "Invalid inline metadata" in error_message
    assert str(bakefile_path) in error_message
    assert "PEP 723 metadata exists but 'bakefile' dependency is missing. " in error_message


def test_find_python_with_no_bakefile(
    tmp_path: Path,
    capfd: pytest.CaptureFixture[str],
) -> None:
    """Case: bakefile.py does not exist - should raise FileNotFoundError."""
    # Arrange ================
    setup_logging(
        level_per_module={"": logging.DEBUG},
        is_pretty_log=False,
    )
    bakefile_path = tmp_path / DEFAULT_FILE_NAME
    # Don't create the bakefile.py file

    # Act ====================
    _ = capfd.readouterr()
    with pytest.raises(PythonNotFoundError) as exc_info:
        find_python_path(bakefile_path)

    # Assert =================
    error_message = str(exc_info.value)
    assert str(bakefile_path) in error_message


class TestFindProjectPythonEdgeCases:
    """Tests for _find_project_python edge cases."""

    def test_find_project_python_returns_none_on_non_zero_returncode(
        self, empty_project_folder_no_inline: Path, capfd: pytest.CaptureFixture[str]
    ) -> None:
        """Case: uv python find returns non-zero returncode."""
        # Arrange ================
        setup_logging(level_per_module={"": logging.DEBUG}, is_pretty_log=False)
        bakefile_path = empty_project_folder_no_inline / DEFAULT_FILE_NAME

        mock_result = MagicMock(spec=subprocess.CompletedProcess)
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "error: some error"

        with patch("bake.manage.find_python.run_uv", return_value=mock_result):
            # Act ====================
            _ = capfd.readouterr()
            result = _find_project_python(bakefile_path)

            # Assert =================
            assert result is None
            logs = capsys_to_logs(capfd)
            assert has_messages_in_logs(logs, ["No project Python found"])

    def test_find_project_python_returns_none_on_pattern_mismatch(
        self, empty_project_folder_no_inline: Path, capfd: pytest.CaptureFixture[str]
    ) -> None:
        """Case: uv python find succeeds but stderr doesn't match expected pattern."""
        # Arrange ================
        setup_logging(level_per_module={"": logging.DEBUG}, is_pretty_log=False)
        bakefile_path = empty_project_folder_no_inline / DEFAULT_FILE_NAME

        mock_result = MagicMock(spec=subprocess.CompletedProcess)
        mock_result.returncode = 0
        mock_result.stdout = "/usr/bin/python3"
        mock_result.stderr = "Some other output that doesn't match pattern"

        with patch("bake.manage.find_python.run_uv", return_value=mock_result):
            # Act ====================
            _ = capfd.readouterr()
            result = _find_project_python(bakefile_path)

            # Assert =================
            assert result is None
            logs = capsys_to_logs(capfd)
            assert has_messages_in_logs(logs, ["No project Python found"])

    def test_find_project_python_returns_none_on_source_mismatch(
        self, empty_project_folder_no_inline: Path, capfd: pytest.CaptureFixture[str]
    ) -> None:
        """Case: stderr matches pattern but source is not virtual environment."""
        # Arrange ================
        setup_logging(level_per_module={"": logging.DEBUG}, is_pretty_log=False)
        bakefile_path = empty_project_folder_no_inline / DEFAULT_FILE_NAME

        mock_result = MagicMock(spec=subprocess.CompletedProcess)
        mock_result.returncode = 0
        mock_result.stdout = "/usr/bin/python3"
        mock_result.stderr = "Found `python3.12` at `/usr/bin/python3.12` (custom)"

        with patch("bake.manage.find_python.run_uv", return_value=mock_result):
            # Act ====================
            _ = capfd.readouterr()
            result = _find_project_python(bakefile_path)

            # Assert =================
            assert result is None
            logs = capsys_to_logs(capfd)
            assert has_messages_in_logs(logs, ["No project Python found"])

    def test_find_project_python_returns_none_on_path_mismatch(
        self, empty_project_folder_no_inline: Path, capfd: pytest.CaptureFixture[str]
    ) -> None:
        """Case: Python path from stderr log doesn't match stdout (inconsistent output)."""
        # Arrange ================
        setup_logging(level_per_module={"": logging.DEBUG}, is_pretty_log=False)
        bakefile_path = empty_project_folder_no_inline / DEFAULT_FILE_NAME

        mock_result = MagicMock(spec=subprocess.CompletedProcess)
        mock_result.returncode = 0
        # stdout has one path
        mock_result.stdout = "/usr/bin/python3.12"
        # stderr has different path
        mock_result.stderr = "Found `python3.12` at `/usr/bin/python3.11` (virtual environment)"

        with patch("bake.manage.find_python.run_uv", return_value=mock_result):
            # Act ====================
            _ = capfd.readouterr()
            result = _find_project_python(bakefile_path)

            # Assert =================
            assert result is None
            logs = capsys_to_logs(capfd)
            assert has_messages_in_logs(
                logs,
                ["Python path mismatch between log and stdout", "No project Python found"],
            )
