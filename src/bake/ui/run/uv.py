import subprocess
from pathlib import Path
from typing import Literal, overload

from typing_extensions import Unpack
from uv import find_uv_bin

from bake.ui.run.main import PopenKwargs, StrOrNoneCompletedProcess, run


@overload
def run_uv(
    cmd: list[str] | tuple[str, ...],
    *,
    capture_output: Literal[True] = True,
    check: bool = True,
    cwd: Path | str | None = None,
    stream: bool = False,
    clean_capture_output: bool = True,
    shell: bool | None = None,
    echo: bool = True,
    dry_run: bool = False,
    keep_temp_file: bool = False,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
    drain_timeout: float | None = 10.0,
    _encoding: str | None = None,
    **kwargs: Unpack[PopenKwargs],
) -> subprocess.CompletedProcess[str]: ...


@overload
def run_uv(
    cmd: list[str] | tuple[str, ...],
    *,
    capture_output: Literal[False],
    check: bool = True,
    cwd: Path | str | None = None,
    stream: bool = False,
    clean_capture_output: bool = True,
    echo: bool = True,
    dry_run: bool = False,
    keep_temp_file: bool = False,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
    drain_timeout: float | None = 10.0,
    _encoding: str | None = None,
    **kwargs: Unpack[PopenKwargs],
) -> subprocess.CompletedProcess[None]: ...


def run_uv(
    cmd: list[str] | tuple[str, ...],
    *,
    capture_output: bool = True,
    check: bool = True,
    cwd: Path | str | None = None,
    stream: bool = False,
    clean_capture_output: bool = True,
    echo: bool = True,
    dry_run: bool = False,
    keep_temp_file: bool = False,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
    drain_timeout: float | None = 10.0,
    _encoding: str | None = None,
    **kwargs: Unpack[PopenKwargs],
) -> StrOrNoneCompletedProcess:
    uv_bin = find_uv_bin()

    return run(
        [uv_bin, *cmd],
        capture_output=capture_output,
        check=check,
        cwd=cwd,
        stream=stream,
        clean_capture_output=clean_capture_output,
        shell=False,
        echo=echo,
        echo_cmd="uv " + " ".join(cmd) if echo else None,
        dry_run=dry_run,
        keep_temp_file=keep_temp_file,
        env=env,
        timeout=timeout,
        drain_timeout=drain_timeout,
        _encoding=_encoding,
        **kwargs,
    )
