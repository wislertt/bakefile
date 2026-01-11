import logging
import subprocess
from pathlib import Path

from bake.manage.find_python import find_python_path, is_standalone_bakefile
from bake.ui import console, style
from bake.ui.run import run, run_uv
from bake.utils import BakebookError
from bake.utils.exceptions import PythonNotFoundError

logger = logging.getLogger(__name__)


def _run_uv(
    bakefile_path: Path | None, command_name: str, cmd: list[str], dry_run: bool = False
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[None]:
    if bakefile_path is None or not bakefile_path.exists():
        raise PythonNotFoundError(f"Bakefile not found at {bakefile_path}")

    if not is_standalone_bakefile(bakefile_path):
        error_msg = (
            f"`{command_name}` command requires PEP 723 inline metadata in the bakefile. "
            f"Run {style.code('bakefile add-inline')} to add metadata, "
            f"or use {style.code(f'uv {command_name}')} directly for project-level dependencies."
        )
        raise BakebookError(error_msg)

    logger.debug(f"Running `uv {command_name}` for {bakefile_path}")
    result = run_uv(
        (command_name, "--script", bakefile_path.name, *cmd),
        capture_output=True,
        stream=True,
        check=True,
        echo=True,
        cwd=bakefile_path.parent,
        dry_run=dry_run,
    )
    return result


def run_uv_add(
    bakefile_path: Path | None, cmd: list[str], dry_run: bool
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[None]:
    return _run_uv(bakefile_path=bakefile_path, command_name="add", cmd=cmd, dry_run=dry_run)


def run_uv_lock(
    bakefile_path: Path | None, cmd: list[str], dry_run: bool
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[None]:
    return _run_uv(bakefile_path=bakefile_path, command_name="lock", cmd=cmd, dry_run=dry_run)


def run_uv_sync(
    bakefile_path: Path | None, cmd: list[str], dry_run: bool
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[None]:
    return _run_uv(bakefile_path=bakefile_path, command_name="sync", cmd=cmd, dry_run=dry_run)


def run_uv_pip(
    bakefile_path: Path | None, cmd: list[str], dry_run: bool
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[None]:
    if bakefile_path is None or not bakefile_path.exists():
        raise PythonNotFoundError(f"Bakefile not found at {bakefile_path}")

    is_standalone = is_standalone_bakefile(bakefile_path)
    if not is_standalone:
        console.warning(
            "No PEP 723 inline metadata found. Using project-level Python.\n"
            f"For project-level dependencies, consider using {style.code('uv pip')} directly.\n"
        )

    python_path = find_python_path(bakefile_path)

    version_result = run(
        [str(python_path), "--version"], capture_output=True, stream=False, echo=False
    )
    version = version_result.stdout.strip() or version_result.stderr.strip()
    console.err.print(f"Using {version}\n")

    logger.debug(f"Running uv pip with cmd: {cmd}")
    return run_uv(
        ("pip", *cmd, "--python", str(python_path)),
        capture_output=True,
        stream=True,
        check=True,
        echo=True,
        dry_run=dry_run,
    )
