import logging
import subprocess

from typing_extensions import Unpack

from bake.ui import console
from bake.ui.run import StrOrNoneCompletedProcess, run
from bake.ui.run.main import RunScriptKwargs

logger = logging.getLogger(__name__)


def argv_to_multiline_cmd(args: list[str]) -> str:
    return " \\\n  ".join(args)


def run_script(
    title: str,
    script: str,
    *,
    capture_output: bool = True,
    **kwargs: Unpack[RunScriptKwargs],
) -> StrOrNoneCompletedProcess:
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

    if kwargs.get("echo", True):
        console.script_block(title, script)

    if kwargs.pop("dry_run", False):
        logger.debug(f"[dry-run] {title}", extra={"cwd": kwargs.get("cwd")})
        return subprocess.CompletedProcess(
            args=script,
            returncode=0,
            stdout="" if capture_output else None,
            stderr="" if capture_output else None,
        )

    # run() must not re-echo: the script block above is the display
    kwargs["echo"] = False
    return run(
        script,
        capture_output=capture_output,
        shell=True,
        **kwargs,
    )
