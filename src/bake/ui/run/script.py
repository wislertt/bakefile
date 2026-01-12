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
    **kwargs,
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[None]:
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
        **kwargs,
    )
