import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Literal, overload

import typer

from bake.ui import console
from bake.ui.run.splitter import OutputSplitter

# Import pty on Unix systems for color-preserving PTY support
if sys.platform != "win32":
    import pty

logger = logging.getLogger(__name__)


@overload
def run(
    cmd: str,
    *,
    capture_output: Literal[True] = True,
    check: bool = True,
    cwd: Path | str | None = None,
    stream: bool = True,
    shell: bool | None = None,
    echo: bool = True,
    dry_run: bool = False,
    **kwargs,
) -> subprocess.CompletedProcess[str]: ...


@overload
def run(
    cmd: str,
    *,
    capture_output: Literal[False],
    check: bool = True,
    cwd: Path | str | None = None,
    stream: bool = True,
    shell: bool | None = None,
    echo: bool = True,
    dry_run: bool = False,
    **kwargs,
) -> subprocess.CompletedProcess[None]: ...


@overload
def run(
    cmd: list[str] | tuple[str, ...],
    *,
    capture_output: Literal[True] = True,
    check: bool = True,
    cwd: Path | str | None = None,
    stream: bool = True,
    shell: bool | None = None,
    echo: bool = True,
    dry_run: bool = False,
    **kwargs,
) -> subprocess.CompletedProcess[str]: ...


@overload
def run(
    cmd: list[str] | tuple[str, ...],
    *,
    capture_output: Literal[False],
    check: bool = True,
    cwd: Path | str | None = None,
    stream: bool = True,
    shell: bool | None = None,
    echo: bool = True,
    dry_run: bool = False,
    **kwargs,
) -> subprocess.CompletedProcess[None]: ...


def run(
    cmd: str | list[str] | tuple[str, ...],
    *,
    capture_output: bool = True,
    check: bool = True,
    cwd: Path | str | None = None,
    stream: bool = True,
    shell: bool | None = None,
    echo: bool = True,
    dry_run: bool = False,
    **kwargs,
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[None]:
    """Run a command with optional streaming and output capture.

    Parameters
    ----------
    cmd : str | list[str] | tuple[str, ...]
        Command as string, list, or tuple of strings.
        String commands automatically use shell=True for shell features
        (pipes, wildcards, chaining). List/tuple commands use shell=False
        for safer direct execution.
    capture_output : bool, optional
        Whether to capture stdout/stderr, by default True.
    check : bool, optional
        Raise typer.Exit on non-zero exit code, by default True.
    cwd : Path | str | None, optional
        Working directory, by default None.
    stream : bool, optional
        Stream output to terminal in real-time, by default True.
        On Unix, uses PTY to preserve ANSI color codes.
    shell : bool | None, optional
        Whether to use shell for command execution, by default None.
        When None (default), auto-detected from command type:
        str → True, list/tuple → False.
        **Security Warning:** Shell=True can be vulnerable to injection
        with untrusted input. Only use with trusted commands.
    echo : bool, optional
        Display command before execution using console.cmd().
        Default is True. Set to False for silent execution.
    dry_run : bool, optional
        Display command without executing (dry-run mode).
        Default is False. Does NOT auto-echo; combine with echo=True
        to preview commands.
    **kwargs
        Additional arguments passed to subprocess.

    Returns
    -------
    subprocess.CompletedProcess[str | None]
        CompletedProcess with stdout/stderr as strings
        (or None if not captured).

    Raises
    ------
    typer.Exit
        When check=True and command returns non-zero exit code.

    Examples
    --------
    >>> run("echo hello")                     # Shows and runs command
    >>> run("echo hello", echo=False)         # Silent execution
    >>> run("echo hello", dry_run=True)       # Silent dry-run
    >>> run("echo hello", echo=True, dry_run=True)  # Show but don't run
    >>> run("ls *.py | wc -l")                # Pipes and wildcards
    >>> run(["echo", "hello"])                # List for direct execution
    """
    _validate_params(stream=stream, capture_output=capture_output)
    shell = _detect_shell(cmd=cmd, shell=shell)
    cmd_str = _format_cmd_str(cmd=cmd)

    if echo:
        console.cmd(cmd_str)

    if dry_run:
        return _dry_run_result(cmd=cmd, capture_output=capture_output, cwd=cwd)

    logger.debug(f"[run] {cmd_str}", extra={"cwd": cwd})
    start = time.perf_counter()

    if stream:
        result = _run_with_stream(
            cmd=cmd,
            shell=shell,
            cwd=cwd,
            capture_output=capture_output,
            **kwargs,
        )
    else:
        result = _run_without_stream(
            cmd=cmd,
            shell=shell,
            cwd=cwd,
            capture_output=capture_output,
            **kwargs,
        )

    _check_exit_code(returncode=result.returncode, check=check, cmd_str=cmd_str)

    _log_completion(cmd_str=cmd_str, result=result, start=start)
    return result


def _validate_params(stream: bool, capture_output: bool) -> None:
    if stream is False and capture_output is False:
        raise ValueError("At least one of `stream` or `capture_output` must be True")


def _detect_shell(cmd: str | list[str] | tuple[str, ...], shell: bool | None) -> bool:
    if shell is None:
        return isinstance(cmd, str)
    return shell


def _format_cmd_str(cmd: str | list[str] | tuple[str, ...]) -> str:
    return cmd if isinstance(cmd, str) else " ".join(cmd)


def _dry_run_result(
    cmd: str | list[str] | tuple[str, ...],
    capture_output: bool,
    cwd: Path | str | None,
) -> subprocess.CompletedProcess[str]:
    cmd_str = _format_cmd_str(cmd)
    logger.debug(f"[dry-run] {cmd_str}", extra={"cwd": cwd})
    return subprocess.CompletedProcess(
        args=cmd,
        returncode=0,
        stdout="" if capture_output else None,
        stderr="" if capture_output else None,
    )


def _check_exit_code(returncode: int, check: bool, cmd_str: str) -> None:
    if check and returncode != 0:
        logger.debug(f"[error] {cmd_str}", extra={"returncode": returncode})
        raise typer.Exit(returncode)


def _process_stream_output(
    splitter: OutputSplitter,
    proc: subprocess.Popen,
    cmd: str | list[str] | tuple[str, ...],
    capture_output: bool,
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[None]:
    stdout: str | None
    stderr: str | None

    if capture_output:
        stdout = splitter.stdout.decode("utf-8", errors="replace")
        stderr = splitter.stderr.decode("utf-8", errors="replace")
        # Normalize PTY line endings (\r\n -> \n)
        stdout = stdout.replace("\r\n", "\n")
        stderr = stderr.replace("\r\n", "\n")
    else:
        stdout = None
        stderr = None

    return subprocess.CompletedProcess(
        args=cmd, returncode=proc.returncode, stdout=stdout, stderr=stderr
    )


def _setup_pty_stream(
    cmd: str | list[str] | tuple[str, ...],
    shell: bool,
    cwd: Path | str | None,
    capture_output: bool,
    **kwargs,
) -> tuple[subprocess.Popen, OutputSplitter]:
    stdout_fd, slave_fd = pty.openpty()

    env = os.environ.copy()
    env.setdefault("FORCE_COLOR", "1")
    env.setdefault("CLICOLOR_FORCE", "1")

    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=slave_fd,
        stderr=subprocess.PIPE if capture_output else None,
        shell=shell,
        env=env,
        **kwargs,
    )
    os.close(slave_fd)

    splitter = OutputSplitter(stream=True, capture=capture_output, pty_fd=stdout_fd)
    return proc, splitter


def _setup_pipe_stream(
    cmd: str | list[str] | tuple[str, ...],
    shell: bool,
    cwd: Path | str | None,
    capture_output: bool,
    **kwargs,
) -> tuple[subprocess.Popen, OutputSplitter]:
    env = kwargs.pop("env", os.environ.copy())
    env.setdefault("FORCE_COLOR", "1")
    env.setdefault("CLICOLOR_FORCE", "1")

    splitter = OutputSplitter(stream=True, capture=capture_output)
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE if capture_output else None,
        stderr=subprocess.PIPE if capture_output else None,
        shell=shell,
        env=env,
        **kwargs,
    )
    return proc, splitter


def _run_with_stream(
    cmd: str | list[str] | tuple[str, ...],
    shell: bool,
    cwd: Path | str | None,
    capture_output: bool,
    **kwargs,
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[None]:
    use_pty = sys.platform != "win32"

    if use_pty:
        proc, splitter = _setup_pty_stream(cmd, shell, cwd, capture_output, **kwargs)
    else:
        proc, splitter = _setup_pipe_stream(cmd, shell, cwd, capture_output, **kwargs)

    threads = splitter.attach(proc)
    proc.wait()
    splitter.finalize(threads)

    return _process_stream_output(splitter, proc, cmd, capture_output)


def _run_without_stream(
    cmd: str | list[str] | tuple[str, ...],
    shell: bool,
    cwd: Path | str | None,
    capture_output: bool,
    **kwargs,
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[None]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=capture_output,
        text=True,
        check=False,
        shell=shell,
        **kwargs,
    )


def _log_completion(cmd_str: str, result: subprocess.CompletedProcess, start: float) -> None:
    elapsed_seconds = time.perf_counter() - start
    logger.debug(
        f"[done] {cmd_str}",
        extra={
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "elapsed_seconds": elapsed_seconds,
        },
    )
