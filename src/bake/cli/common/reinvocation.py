import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Literal

from bake.utils.settings import ENV__BAKE_REINVOKED, bake_settings

logger = logging.getLogger(__name__)

CliModule = Literal["bake.cli.bake", "bake.cli.bakefile"]


def _reinvoke_with_detected_python(bakefile_path: Path | None, *, cli_module: CliModule) -> None:
    """Re-invoke CLI with detected Python if needed.

    Checks if the current Python is the correct one for the bakefile.
    If not, re-invokes the CLI with the detected Python.

    Args:
        bakefile_path: Path to the bakefile, or None if not found
        cli_module: The CLI module to reinvoke ("bake.cli.bake" or "bake.cli.bakefile")

    Returns:
        None. Either calls subprocess and exits, or returns normally.
    """
    logger.debug("Starting _reinvoke_with_detected_python")

    # 1. Check marker to prevent infinite loops
    if bake_settings.bake_reinvoked:
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
        f"Re-invoking with detected Python: {target_python} (current: {current_python})",
        extra={"target_python": str(target_python), "cli_module": cli_module},
    )
    env = os.environ.copy()
    env[ENV__BAKE_REINVOKED] = "1"

    sys.stdout.flush()
    sys.stderr.flush()
    try:
        result = subprocess.run(
            [str(target_python), "-m", cli_module, *sys.argv[1:]],
            env=env,
        )
        raise SystemExit(result.returncode)
    except KeyboardInterrupt as e:
        # User pressed Ctrl+C - exit cleanly with standard SIGINT exit code (128 + 2)
        raise SystemExit(130) from e
