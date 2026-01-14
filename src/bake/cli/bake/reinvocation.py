import logging
import os
import subprocess
import sys
from pathlib import Path

from bake.utils.env import _BAKE_REINVOKED

logger = logging.getLogger(__name__)


def _reinvoke_with_detected_python(bakefile_path: Path | None) -> None:
    """Re-invoke bake CLI with detected Python if needed.

    Checks if the current Python is the correct one for the bakefile.
    If not, re-invokes the bake CLI with the detected Python using os.execve().

    Args:
        bakefile_path: Path to the bakefile, or None if not found

    Returns:
        None. Either calls os.execve() (replaces process) or returns normally.
    """
    # 1. Check marker to prevent infinite loops
    if os.environ.get(_BAKE_REINVOKED):
        logger.debug(
            "Re-invocation marker set, skipping Python check",
            extra={"sys.executable": sys.executable},
        )
        return

    # 2. Try to find correct Python
    try:
        from bake.manage.find_python import find_python_path

        python_path = find_python_path(bakefile_path)
    except Exception:
        logger.debug("Failed to find Python for bakefile, continuing with current Python")
        return  # Continue with current Python

    # 3. Compare with current Python (don't resolve symlinks - we want the venv Python)
    current_python = Path(sys.executable)
    target_python = python_path

    if current_python == target_python:
        logger.debug(f"Already using correct Python: {current_python}")
        return  # Already correct

    # 4. Re-invoke with detected Python
    logger.debug(
        f"Re-invoking bake with detected Python: {target_python} (current: {current_python})",
        extra={"target_python": str(target_python)},
    )
    env = os.environ.copy()
    env[_BAKE_REINVOKED] = "1"

    sys.stdout.flush()
    sys.stderr.flush()
    result = subprocess.run(
        [str(target_python), "-m", "bake.cli.bake", *sys.argv[1:]],
        env=env,
    )
    raise SystemExit(result.returncode)
