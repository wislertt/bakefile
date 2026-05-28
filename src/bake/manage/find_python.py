import logging
import re
from pathlib import Path

from bake.manage.add_inline import read_inline
from bake.ui import run_uv
from bake.utils import BakebookError
from bake.utils.exceptions import PythonNotFoundError

logger = logging.getLogger(__name__)

_NO_PROJECT_PYTHON_MSG = "No project Python found"


def is_standalone_bakefile(bakefile_path: Path) -> bool:
    inline_metadata = read_inline(bakefile_path)
    if inline_metadata is None:
        return False

    dependencies = inline_metadata.get("dependencies", [])
    has_bakefile = any(dep.startswith("bakefile") for dep in dependencies)

    if not has_bakefile:
        logger.error(
            f"Invalid inline metadata in {bakefile_path}: "
            f"PEP 723 metadata exists but 'bakefile' dependency is missing"
        )
        raise BakebookError(
            f"Invalid inline metadata in {bakefile_path}: "
            f"PEP 723 metadata exists but 'bakefile' dependency is missing. "
            f"Run 'bakefile add-inline' to fix."
        )

    return True


def _find_project_root(bakefile_path: Path) -> Path | None:
    """Find directory containing pyproject.toml by searching up from bakefile's parent."""
    current = bakefile_path.parent
    if (current / "pyproject.toml").exists():
        logger.debug(f"Found project root at {current}")
        return current
    for directory in current.parents:
        if (directory / "pyproject.toml").exists():
            logger.debug(f"Found project root at {directory}")
            return directory
    return None


def _find_bakefile_lock(bakefile_path: Path) -> Path | None:
    """Find bakefile-level lock (<bakefile.py.lock>)."""
    lock_path = bakefile_path.with_suffix(bakefile_path.suffix + ".lock")
    if lock_path.exists():
        logger.debug(f"Found bakefile lock at {lock_path}")
        return lock_path
    logger.debug("No bakefile lock found")
    return None


def _find_project_lock(project_root: Path) -> Path | None:
    lock_path = project_root / "uv.lock"
    if lock_path.exists():
        logger.debug(f"Found project lock at {lock_path}")
        return lock_path
    logger.debug("No project lock found")
    return None


def _find_bakefile_python(bakefile_path: Path) -> Path | None:
    # References:
    #   https://github.com/astral-sh/uv/blob/543f1f3f5924d1d2734fd718381e6f0d0f6f70b5/crates/uv/src/commands/project/mod.rs#L843

    kind = "script"
    found_bakefile_level_venv_message = (
        f"The {kind} environment's Python version satisfies the request"
    )
    result = run_uv(
        ["python", "find", "--script", str(bakefile_path.name), "-v"],
        check=False,
        cwd=bakefile_path.parent,
        echo=False,
    )

    is_bakefile_python_found = (
        result.returncode == 0 and found_bakefile_level_venv_message in result.stderr.strip()
    )

    if is_bakefile_python_found:
        python_path = Path(result.stdout.strip())
        logger.debug(f"Found bakefile Python at {python_path.as_posix()}")
        return python_path

    logger.debug("No bakefile Python found")
    return None


def _find_project_python(project_root: Path) -> Path | None:
    """Find Python from project-level venv using uv python find -v."""
    # References:
    #   https://github.com/astral-sh/uv/blob/543f1f3f5924d1d2734fd718381e6f0d0f6f70b5/crates/uv-python/src/discovery.rs#L795
    #   https://github.com/astral-sh/uv/blob/543f1f3f5924d1d2734fd718381e6f0d0f6f70b5/crates/uv-python/src/discovery.rs#L3169-L3184
    result = run_uv(
        ["python", "find", "-v"],
        check=False,
        cwd=project_root,
        echo=False,
    )

    # Check if stderr contains "Found `...` at `...` (...)"
    # where source is "active virtual environment" or "virtual environment"
    stderr = result.stderr.strip()
    pattern = r"Found `[^`]+` at `([^`]+)` \(([^)]+)\)"
    match = re.search(pattern, stderr)

    if not (result.returncode == 0 and match):
        logger.debug(_NO_PROJECT_PYTHON_MSG)
        return None

    source = match.group(2)
    if source not in {"active virtual environment", "virtual environment"}:
        logger.debug(_NO_PROJECT_PYTHON_MSG)
        return None

    python_path_from_log = Path(match.group(1))
    python_path_from_stdout = Path(result.stdout.strip())
    if python_path_from_log != python_path_from_stdout:
        logger.debug(
            "Python path mismatch between log and stdout",
            extra={
                "python_path_from_log": python_path_from_log,
                "python_path_from_stdout": python_path_from_stdout,
            },
        )
        logger.debug(_NO_PROJECT_PYTHON_MSG)
        return None

    logger.debug(f"Found project Python at {python_path_from_stdout} (source: {source})")
    return python_path_from_stdout


def _create_bakefile_venv(bakefile_path: Path) -> Path | None:
    """Create bakefile-level venv and return Python path."""
    lock_path = _find_bakefile_lock(bakefile_path)

    if lock_path:
        # Use frozen sync if lock exists
        logger.debug("Syncing bakefile with frozen lock")
        run_uv(
            ["sync", "--script", str(bakefile_path.name), "--frozen"],
            check=True,
            cwd=bakefile_path.parent,
            echo=False,
        )
    else:
        # Create new lock and sync
        logger.debug("Creating bakefile lock and syncing")
        run_uv(
            ["sync", "--script", str(bakefile_path.name)],
            check=True,
            cwd=bakefile_path.parent,
            echo=False,
        )
        run_uv(
            ["lock", "--script", str(bakefile_path.name)],
            check=True,
            cwd=bakefile_path.parent,
            echo=False,
        )

    return _find_bakefile_python(bakefile_path)


def _create_project_venv(project_root: Path) -> Path | None:
    """Create project-level venv and return Python path."""
    lock_path = _find_project_lock(project_root)

    if lock_path:
        # Use frozen sync if lock exists
        logger.debug("Syncing project with frozen lock")
        run_uv(["sync", "--frozen"], check=True, cwd=project_root, echo=False)
    else:
        # Create new lock and sync
        logger.debug("Creating project lock and syncing")
        run_uv(["lock"], check=True, cwd=project_root, echo=False)
        run_uv(["sync"], check=True, cwd=project_root, echo=False)

    return _find_project_python(project_root)


def find_python_path(bakefile_path: Path | None) -> Path:
    if bakefile_path is None or not bakefile_path.exists():
        raise PythonNotFoundError(f"Bakefile not found at {bakefile_path}")

    is_standalone = is_standalone_bakefile(bakefile_path)

    if is_standalone:
        logger.debug("Bakefile has inline metadata -> bakefile-level Python")

        # Step 1: Try to find existing bakefile-level Python
        python_path = _find_bakefile_python(bakefile_path)
        if python_path:
            return python_path

        # Step 2: Create bakefile-level venv
        python_path = _create_bakefile_venv(bakefile_path)
        if python_path:
            return python_path

    else:
        logger.debug("No inline metadata -> project-level Python")

        # project_root = directory containing pyproject.toml
        project_root = _find_project_root(bakefile_path)
        if project_root is None:
            raise PythonNotFoundError(
                f"No pyproject.toml found in {bakefile_path.parent} or any parent directory. "
                f"Create a pyproject.toml or run 'bakefile add-inline' for bakefile-level Python."
            )

        # Step 1: Try to find existing project-level Python
        python_path = _find_project_python(project_root)
        if python_path:
            return python_path

        # Step 2: Create project-level venv
        python_path = _create_project_venv(project_root)
        if python_path:
            return python_path

    raise PythonNotFoundError(
        f"Could not find Python for {bakefile_path}. "
        f"Run 'bakefile add-inline' to add PEP 723 metadata for bakefile-level Python."
    )
