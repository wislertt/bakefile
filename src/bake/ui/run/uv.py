import subprocess
from typing import Literal, overload

from typing_extensions import Unpack
from uv import find_uv_bin

from bake.ui.run.main import RunUvKwargs, StrOrNoneCompletedProcess, run


@overload
def run_uv(
    cmd: list[str] | tuple[str, ...],
    *,
    capture_output: Literal[True] = True,
    **kwargs: Unpack[RunUvKwargs],
) -> subprocess.CompletedProcess[str]: ...


@overload
def run_uv(
    cmd: list[str] | tuple[str, ...],
    *,
    capture_output: Literal[False],
    **kwargs: Unpack[RunUvKwargs],
) -> subprocess.CompletedProcess[None]: ...


def run_uv(
    cmd: list[str] | tuple[str, ...],
    *,
    capture_output: bool = True,
    **kwargs: Unpack[RunUvKwargs],
) -> StrOrNoneCompletedProcess:
    uv_bin = find_uv_bin()
    echo = kwargs.get("echo", True)
    # run() streams by default; run_uv callers expect quiet capture (stream=False)
    kwargs.setdefault("stream", False)

    return run(
        [uv_bin, *cmd],
        capture_output=capture_output,
        shell=False,
        echo_cmd="uv " + " ".join(cmd) if echo else None,
        **kwargs,
    )
