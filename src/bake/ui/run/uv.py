import subprocess
from pathlib import Path
from typing import Literal, overload

from uv import find_uv_bin

from bake.ui import console
from bake.ui.run.run import run


@overload
def run_uv(
    cmd: list[str] | tuple[str, ...],
    *,
    capture_output: Literal[True] = True,
    check: bool = True,
    cwd: Path | str | None = None,
    stream: bool = False,
    shell: bool | None = None,
    echo: bool = True,
    dry_run: bool = False,
    keep_temp_file: bool = False,
    env: dict[str, str] | None = None,
    _encoding: str | None = None,
    **kwargs,
) -> subprocess.CompletedProcess[str]: ...


@overload
def run_uv(
    cmd: list[str] | tuple[str, ...],
    *,
    capture_output: Literal[False],
    check: bool = True,
    cwd: Path | str | None = None,
    stream: bool = False,
    echo: bool = True,
    dry_run: bool = False,
    keep_temp_file: bool = False,
    env: dict[str, str] | None = None,
    _encoding: str | None = None,
    **kwargs,
) -> subprocess.CompletedProcess[None]: ...


def run_uv(
    cmd: list[str] | tuple[str, ...],
    *,
    capture_output: bool = True,
    check: bool = True,
    cwd: Path | str | None = None,
    stream: bool = False,
    echo: bool = True,
    dry_run: bool = False,
    keep_temp_file: bool = False,
    env: dict[str, str] | None = None,
    _encoding: str | None = None,
    **kwargs,
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[None]:
    uv_bin = find_uv_bin()

    # Build display string: "uv" + command parts (no full binary path)
    display_cmd = "uv " + " ".join(cmd)

    # Echo command to console if requested
    if echo:
        console.cmd(display_cmd)

    # Call run with full uv binary path, echo=False (already displayed), pass through options
    return run(
        [uv_bin, *cmd],
        capture_output=capture_output,
        check=check,
        cwd=cwd,
        stream=stream,
        shell=False,
        echo=False,
        dry_run=dry_run,
        keep_temp_file=keep_temp_file,
        env=env,
        _encoding=_encoding,
        **kwargs,
    )
