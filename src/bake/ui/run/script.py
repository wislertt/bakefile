import logging
import subprocess
from pathlib import Path

from bake.ui import console
from bake.ui.run import run

logger = logging.getLogger(__name__)


def run_script(
    title: str,
    script: str,
    *,
    capture_output: bool = True,
    check: bool = True,
    cwd: Path | str | None = None,
    stream: bool = True,
    echo: bool = True,
    dry_run: bool = False,
    keep_temp_file: bool = False,
    env: dict[str, str] | None = None,
    **kwargs,
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[None]:
    """Run a multi-line script with shebang support.

    Creates a temporary file with the script content and executes it. On Unix,
    the file is made executable and run directly (kernel handles shebang). On
    Windows, the shebang is parsed and the interpreter is invoked explicitly.

    For cross-platform UTF-8 support in scripts with non-ASCII characters, pass
    appropriate environment variables. Example for Python scripts:
        run_script("My Script", script, env={"PYTHONIOENCODING": "utf-8"})

    Parameters
    ----------
    title : str
        Display title for the script (shown in console output).
    script : str
        Multi-line script content to execute.
    env : dict[str, str] | None, optional
        Environment variables for the subprocess. Merged with system environment
        to preserve critical variables like SYSTEMROOT on Windows. User-provided
        variables override defaults.
    **kwargs
        Additional arguments passed to :func:`run`. Common options include:
        - keep_temp_file: bool to skip temp file cleanup (for debugging)
    """
    script = script.strip()

    if echo:
        console.script_block(title, script)

    if dry_run:
        logger.debug(f"[dry-run] {title}", extra={"cwd": cwd})
        return subprocess.CompletedProcess(
            args=script,
            returncode=0,
            stdout="" if capture_output else None,
            stderr="" if capture_output else None,
        )

    return run(
        script,
        capture_output=capture_output,
        check=check,
        cwd=cwd,
        stream=stream,
        echo=False,
        shell=True,
        keep_temp_file=keep_temp_file,
        env=env,
        **kwargs,
    )
