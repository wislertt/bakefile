import logging
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, overload

import typer

from bake.ui import console
from bake.ui.run.splitter import OutputSplitter

# Import pty on Unix systems for color-preserving PTY support
if sys.platform != "win32":
    import pty

logger = logging.getLogger(__name__)

# Lock for subprocess.Popen calls - subprocess is not thread-safe by design
# See: https://bugs.python.org/issue2320, https://bugs.python.org/issue12739
_subprocess_create_lock = threading.Lock()


@dataclass(frozen=True, slots=True)
class StreamSetup:
    proc: subprocess.Popen
    splitter: OutputSplitter
    threads: list


def _parse_shebang(script: str) -> str | None:
    """Parse shebang line, return interpreter path or None."""
    lines = script.strip().splitlines()
    if not lines or not lines[0].startswith("#!"):
        return None

    shebang = lines[0][2:].strip()

    # Handle /usr/bin/env XXX
    if shebang.startswith("/usr/bin/env "):
        interpreter = shebang.split()[1]  # Get "python3" from "/usr/bin/env python3"
        return _resolve_interpreter(interpreter)

    # Direct path like /usr/bin/python3
    return shebang


def _resolve_interpreter(interpreter: str) -> str | None:
    """Resolve interpreter path, handling cross-platform differences."""
    # If it's an absolute path, use as-is
    if os.path.isabs(interpreter):
        return interpreter if os.path.exists(interpreter) else None

    # Search in PATH
    return shutil.which(interpreter)


def _run_with_temp_file(
    cmd: str,
    capture_output: bool,
    check: bool,
    cwd: Path | str | None,
    stream: bool,
    keep_temp_file: bool = False,
    env: dict[str, str] | None = None,
    _encoding: str = "utf-8",
    **kwargs,
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[None]:
    """Run multi-line script using temp file with shebang support.

    On Windows: Parse shebang and use interpreter explicitly, or use cmd.exe /c.
    On Unix: Make file executable and run directly (kernel handles shebang).

    Parameters
    ----------
    keep_temp_file : bool, optional
        If True, skip deletion of temp file for debugging. Default is False.
    _encoding : str, optional
        Encoding to use for subprocess output. Defaults to "utf-8" to ensure
        cross-platform UTF-8 support for temp file scripts.

    Notes
    -----
    Cross-platform UTF-8 support: On Windows, console encoding defaults to cp1252.
    For scripts that output UTF-8 characters (non-ASCII, emoji, etc.), users should
    pass appropriate environment variables:

    - Python: env={"PYTHONIOENCODING": "utf-8"}
    - Node.js: env={"NODE_OPTIONS": "--input-type=module"} or similar
    - Other interpreters: consult their documentation for UTF-8 environment variables
    """
    # Create temp file with appropriate extension
    suffix = ".bat" if sys.platform == "win32" else ".sh"
    fd, path = tempfile.mkstemp(suffix=suffix)

    try:
        # Write script to temp file
        os.write(fd, cmd.encode("utf-8"))
        os.close(fd)

        # Check for shebang
        interpreter = _parse_shebang(cmd)

        # Determine command based on platform
        if sys.platform == "win32":
            # Windows: Parse shebang and use interpreter explicitly
            cmd_to_run: list[str] = [interpreter, path] if interpreter else ["cmd.exe", "/c", path]
        else:
            # Unix: Make file executable and run directly (kernel handles shebang)
            os.chmod(path, 0o700)  # rwx------ (owner only, more secure)
            cmd_to_run: list[str] = [path]

        return run(
            cmd=cmd_to_run,
            capture_output=capture_output,
            check=check,
            cwd=cwd,
            stream=stream,
            echo=False,
            env=env,
            _encoding=_encoding,
            **kwargs,
        )
    finally:
        # Clean up temp file unless keep_temp_file is True
        if keep_temp_file:
            logger.debug(f"Temp file kept for debugging: {path}")
        elif os.path.exists(path):
            os.unlink(path)


CmdType = str | list[str] | tuple[str, ...]


@overload
def run(
    cmd: CmdType,
    *,
    capture_output: Literal[True] = True,
    check: bool = True,
    cwd: Path | str | None = None,
    stream: bool = True,
    shell: bool | None = None,
    echo: bool = True,
    dry_run: bool = False,
    keep_temp_file: bool = False,
    env: dict[str, str] | None = None,
    _encoding: str | None = None,
    **kwargs,
) -> subprocess.CompletedProcess[str]: ...


@overload
def run(
    cmd: CmdType,
    *,
    capture_output: Literal[False],
    check: bool = True,
    cwd: Path | str | None = None,
    stream: bool = True,
    shell: bool | None = None,
    echo: bool = True,
    dry_run: bool = False,
    keep_temp_file: bool = False,
    env: dict[str, str] | None = None,
    _encoding: str | None = None,
    **kwargs,
) -> subprocess.CompletedProcess[None]: ...


def run(
    cmd: CmdType,
    *,
    capture_output: bool = True,
    check: bool = True,
    cwd: Path | str | None = None,
    stream: bool = True,
    shell: bool | None = None,
    echo: bool = True,
    dry_run: bool = False,
    keep_temp_file: bool = False,
    env: dict[str, str] | None = None,
    _encoding: str | None = None,
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
    keep_temp_file : bool, optional
        Keep temporary script files for debugging instead of deleting them.
        Only applies when temp files are created (multi-line scripts on Windows
        or scripts with shebang). Default is False. Logs temp file path when True.
    env : dict[str, str] | None, optional
        Environment variables for the subprocess. Merged with system environment
        to preserve critical variables like SYSTEMROOT on Windows. User-provided
        variables override defaults. Default is None (use system environment).
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

    # Handle multi-line scripts that require temp file approach:
    # - Windows: Any multi-line script with shell=True (cmd.exe limitation)
    # - Any platform: Scripts with shebang (need file for kernel/interpreter)
    cmd_str_for_shebang = cmd if isinstance(cmd, str) else ""
    has_shebang = cmd_str_for_shebang.strip().startswith("#!")

    # Main condition: string command with shell=True
    if isinstance(cmd, str) and shell:
        # Type narrowing: string_cmd is now known to be str
        string_cmd = cmd
        # Sub-conditions that require temp file:
        # 1. Windows with multi-line script
        # 2. Any platform with shebang
        needs_temp_file = (sys.platform == "win32" and "\n" in string_cmd) or has_shebang
    else:
        needs_temp_file = False
        string_cmd = ""  # Placeholder, won't be used when needs_temp_file=False

    if needs_temp_file:
        return _run_with_temp_file(
            cmd=string_cmd,
            capture_output=capture_output,
            check=check,
            cwd=cwd,
            stream=stream,
            keep_temp_file=keep_temp_file,
            env=env,
            **kwargs,
        )

    logger.debug(f"[run] {cmd_str}", extra={"cwd": cwd})
    start = time.perf_counter()

    _run = _run_with_stream if stream else _run_without_stream

    result = _run(
        cmd=cmd,
        shell=shell,
        cwd=cwd,
        capture_output=capture_output,
        env=env,
        _encoding=_encoding,
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
        encoding = splitter._encoding or "utf-8"
        stdout = splitter.stdout.decode(encoding, errors="replace")
        stderr = splitter.stderr.decode(encoding, errors="replace")
        # Normalize PTY line endings (\r\n -> \n)
        stdout = stdout.replace("\r\n", "\n")
        stderr = stderr.replace("\r\n", "\n")
    else:
        stdout = None
        stderr = None

    return subprocess.CompletedProcess(
        args=cmd, returncode=proc.returncode, stdout=stdout, stderr=stderr
    )


def _prepare_subprocess_env(env: dict[str, str] | None = None) -> dict[str, str]:
    # Always start with system environment to preserve critical variables like
    # SYSTEMROOT on Windows (required for Python initialization - see Prefect #4923)
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    merged_env.setdefault("FORCE_COLOR", "1")
    merged_env.setdefault("CLICOLOR_FORCE", "1")
    try:
        terminal_size = os.get_terminal_size()
        merged_env.setdefault("COLUMNS", str(terminal_size.columns))
        merged_env.setdefault("LINES", str(terminal_size.lines))
    except OSError:
        pass
    return merged_env


def _setup_pty_stream(
    cmd: str | list[str] | tuple[str, ...],
    shell: bool,
    cwd: Path | str | None,
    capture_output: bool,
    env: dict[str, str] | None = None,
    _encoding: str | None = None,
    **kwargs,
) -> StreamSetup:
    # subprocess.Popen is not thread-safe, protect with lock
    # See: https://bugs.python.org/issue2320
    with _subprocess_create_lock:
        stdout_fd, slave_stdout = pty.openpty()

        # Always create stderr PTY when streaming to ensure output goes through
        # our thread which writes to sys.stderr (allows pytest to capture it)
        stderr_fd, slave_stderr = pty.openpty()

        env = _prepare_subprocess_env(env)
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=slave_stdout,
            stderr=slave_stderr,
            shell=shell,
            env=env,
            **kwargs,
        )
        os.close(slave_stdout)
        os.close(slave_stderr)

    # Attach threads BEFORE releasing lock to ensure reader is ready
    # when fast-exiting processes complete
    splitter = OutputSplitter(
        stream=True,
        capture=capture_output,
        pty_fd=stdout_fd,
        stderr_pty_fd=stderr_fd,
        encoding=_encoding,
    )
    threads = splitter.attach(proc)

    return StreamSetup(proc=proc, splitter=splitter, threads=threads)


def _setup_pipe_stream(
    cmd: str | list[str] | tuple[str, ...],
    shell: bool,
    cwd: Path | str | None,
    capture_output: bool,
    env: dict[str, str] | None = None,
    _encoding: str | None = None,
    **kwargs,
) -> StreamSetup:
    # subprocess.Popen is not thread-safe, protect with lock
    # See: https://bugs.python.org/issue2320
    with _subprocess_create_lock:
        env = _prepare_subprocess_env(env)
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=shell,
            env=env,
            **kwargs,
        )
        # Attach threads BEFORE releasing lock to ensure reader is ready
        # when fast-exiting processes complete
        splitter = OutputSplitter(stream=True, capture=capture_output, encoding=_encoding)
        threads = splitter.attach(proc)

    return StreamSetup(proc=proc, splitter=splitter, threads=threads)


def _run_with_stream(
    cmd: str | list[str] | tuple[str, ...],
    shell: bool,
    cwd: Path | str | None,
    capture_output: bool,
    env: dict[str, str] | None = None,
    _encoding: str | None = None,
    **kwargs,
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[None]:
    use_pty = sys.platform != "win32"

    _setup = _setup_pty_stream if use_pty else _setup_pipe_stream

    setup = _setup(
        cmd=cmd,
        shell=shell,
        cwd=cwd,
        capture_output=capture_output,
        env=env,
        _encoding=_encoding,
        **kwargs,
    )

    setup.proc.wait()
    setup.splitter.finalize(setup.threads)

    return _process_stream_output(setup.splitter, setup.proc, cmd, capture_output)


def _run_without_stream(
    cmd: str | list[str] | tuple[str, ...],
    shell: bool,
    cwd: Path | str | None,
    capture_output: bool,
    env: dict[str, str] | None = None,
    _encoding: str | None = None,
    **kwargs,
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[None]:
    # Prepare environment (merges with system env to preserve SYSTEMROOT on Windows)
    env = _prepare_subprocess_env(env)

    # Use specified encoding with errors="replace", or fall back to text=True (platform default)
    if _encoding:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=capture_output,
            check=False,
            shell=shell,
            env=env,
            encoding=_encoding,
            errors="replace",
            **kwargs,
        )
    else:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            check=False,
            shell=shell,
            env=env,
            **kwargs,
        )

    return result


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
