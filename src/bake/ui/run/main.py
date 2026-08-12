import contextlib
import logging
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, overload

import typer
from rich.text import Text

from bake.ui import console, style
from bake.ui.run.splitter import OutputSplitter
from bake.utils.settings import ENV__BAKE_REINVOKED

# CompletedProcess is invariant in T, so this is a str|None union, not [str | None].
StrOrNoneCompletedProcess = subprocess.CompletedProcess[str] | subprocess.CompletedProcess[None]

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
    timeout: float | None = None,
    _encoding: str | None = None,
    echo_cmd: str | None = None,
    **kwargs,
) -> StrOrNoneCompletedProcess:
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
    echo_cmd : str | None, optional
        Override the command string displayed in logs and console output.
        Default is None (show actual command).

    Notes
    -----
    Cross-platform UTF-8 support: On Windows, console encoding defaults to cp1252.
    For scripts that output UTF-8 characters (non-ASCII, emoji, etc.), users should
    pass appropriate environment variables:

    - Python: env={"PYTHONIOENCODING": "utf-8"}
    - Node.js: env={"NODE_OPTIONS": "--input-type=module"} or similar
    - Other interpreters: consult their documentation for UTF-8 environment variables
    """
    # Determine temp file extension and shell for Windows
    if sys.platform == "win32":
        sh_path = shutil.which("sh.exe")
        if not sh_path:
            raise RuntimeError(
                "sh.exe not found. Please install Git for Windows to use shell "
                "commands on Windows. See https://git-scm.com/download/win"
            )
        suffix = ".sh"
    else:
        sh_path = None
        suffix = ".sh"

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
            if interpreter:
                cmd_to_run: list[str] = [interpreter, path]
            else:
                cmd_to_run = [sh_path, path]
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
            echo_cmd=echo_cmd,
            env=env,
            timeout=timeout,
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
    echo_cmd: str | None = None,
    dry_run: bool = False,
    keep_temp_file: bool = False,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
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
    echo_cmd: str | None = None,
    dry_run: bool = False,
    keep_temp_file: bool = False,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
    _encoding: str | None = None,
    **kwargs,
) -> subprocess.CompletedProcess[None]: ...


def run(
    cmd: CmdType,
    *,
    capture_output: bool = False,
    check: bool = True,
    cwd: Path | str | None = None,
    stream: bool = True,
    shell: bool | None = None,
    echo: bool = True,
    echo_cmd: str | None = None,
    dry_run: bool = False,
    keep_temp_file: bool = False,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
    _encoding: str | None = None,
    **kwargs,
) -> StrOrNoneCompletedProcess:
    """Run a command with optional streaming and output capture.

    Parameters
    ----------
    cmd : str | list[str] | tuple[str, ...]
        Command as string, list, or tuple of strings.
        String commands automatically use shell=True for shell features
        (pipes, wildcards, chaining). List/tuple commands use shell=False
        for safer direct execution.
    capture_output : bool
        Whether to capture stdout/stderr, by default False.
        **Note:** When combined with ``stream=True``, interactive or progressive
        output (spinners, progress bars, cursor movements) may not display
        correctly. For interactive commands, use ``capture_output=False``.
    check : bool
        Raise typer.Exit on non-zero exit code, by default True.
    cwd : Path | str | None, optional
        Working directory, by default None.
    stream : bool
        Stream output to terminal in real-time, by default True.
        On Unix, uses PTY to preserve ANSI color codes.
    shell : bool | None, optional
        Whether to use shell for command execution, by default None.
        When None (default), auto-detected from command type:
        str → True, list/tuple → False.
        **Security Warning:** Shell=True can be vulnerable to injection
        with untrusted input. Only use with trusted commands.
    echo : bool
        Display command before execution using console.cmd().
        Default is True. Set to False for silent execution.
    echo_cmd : str | None, optional
        Override the command string displayed in logs and console output.
        The actual command is still executed, but this string is shown instead.
        Useful for hiding complex binary paths or secrets in commands.
        Default is None (show actual command).
    dry_run : bool
        Display command without executing (dry-run mode).
        Default is False. Does NOT auto-echo; combine with echo=True
        to preview commands.
    keep_temp_file : bool
        Keep temporary script files for debugging instead of deleting them.
        Only applies when temp files are created (multi-line scripts on Windows
        or scripts with shebang). Default is False. Logs temp file path when True.
    env : dict[str, str] | None, optional
        Environment variables for the subprocess. Merged with system environment
        to preserve critical variables like SYSTEMROOT on Windows. User-provided
        variables override defaults. Default is None (use system environment).
    timeout : float | None, optional
        Maximum time in seconds to wait for the command to complete.
        If the command exceeds this time, it will be killed and
        subprocess.TimeoutExpired will be raised. Default is None (no timeout).
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
    subprocess.TimeoutExpired
        When timeout is exceeded.

    Notes
    -----
    When ``stream=True`` and ``capture_output=True``, interactive or progressive
    output (spinners, progress bars, cursor movements) may not display correctly.
    For interactive commands, use ``stream=True, capture_output=False`` instead.

    Examples
    --------
    >>> run("echo hello")                     # Shows and runs command
    >>> run("echo hello", echo=False)         # Silent execution
    >>> run("echo hello", dry_run=True)       # Silent dry-run
    >>> run("echo hello", echo=True, dry_run=True)  # Show but don't run
    >>> run("ls *.py | wc -l")                # Pipes and wildcards
    >>> run(["echo", "hello"])                # List for direct execution
    >>> run("/path/to/binary arg", echo_cmd="binary arg")  # Override display
    >>> run("slow-command", timeout=30)       # Timeout after 30 seconds
    """
    _validate_params(stream=stream, capture_output=capture_output)
    shell = _detect_shell(cmd=cmd, shell=shell)
    cmd_str = _format_cmd_str(cmd=cmd)
    cmd_str_for_display = echo_cmd if echo_cmd is not None else cmd_str

    if echo:
        console.cmd(cmd_str_for_display)

    if dry_run:
        return _dry_run_result(cmd=cmd, capture_output=capture_output, cwd=cwd, echo_cmd=echo_cmd)

    # Handle multi-line scripts that require temp file approach:
    # - Windows: Any multi-line script with shell=True (cmd.exe limitation)
    # - Any platform: Scripts with shebang (need file for kernel/interpreter)
    # IMPORTANT: Check shebang BEFORE _use_sh_on_windows() since that converts cmd to list
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
            timeout=timeout,
            _encoding=_encoding,
            echo_cmd=echo_cmd,
            **kwargs,
        )

    # Apply Windows shell conversion only if NOT going to temp file path
    # (temp file path handles shebangs and multi-line scripts separately)
    cmd, shell = _use_sh_on_windows(cmd=cmd, shell=shell)

    logger.debug(f"[run] {cmd_str_for_display}", extra={"cwd": cwd})
    start = time.perf_counter()

    _run = _run_with_split if (stream and capture_output) else _run_without_split

    result = _run(
        cmd=cmd,
        shell=shell,
        cwd=cwd,
        capture_output=capture_output,
        env=env,
        timeout=timeout,
        _encoding=_encoding,
        **kwargs,
    )

    _check_exit_code(
        result=result, check=check, cmd_str_for_display=cmd_str_for_display, stream=stream
    )

    _log_completion(cmd_str_for_display=cmd_str_for_display, result=result, start=start)
    return result


def _validate_params(stream: bool, capture_output: bool) -> None:
    if stream is False and capture_output is False:
        raise ValueError("At least one of `stream` or `capture_output` must be True")


def _detect_shell(cmd: str | list[str] | tuple[str, ...], shell: bool | None) -> bool:
    if shell is None:
        return isinstance(cmd, str)
    return shell


def _use_sh_on_windows(
    cmd: str | list[str] | tuple[str, ...],
    shell: bool,
) -> tuple[str | list[str] | tuple[str, ...], bool]:
    if not (sys.platform == "win32" and shell and isinstance(cmd, str)):
        return cmd, shell

    sh_path = shutil.which("sh.exe")
    if not sh_path:
        raise RuntimeError(
            "sh.exe not found. Please install Git for Windows to use shell "
            "commands on Windows. See https://git-scm.com/download/win"
        )
    return [sh_path, "-c", cmd], False


def _format_cmd_str(cmd: str | list[str] | tuple[str, ...]) -> str:
    return cmd if isinstance(cmd, str) else " ".join(cmd)


def _dry_run_result(
    cmd: str | list[str] | tuple[str, ...],
    capture_output: bool,
    cwd: Path | str | None,
    echo_cmd: str | None = None,
) -> subprocess.CompletedProcess[str]:
    cmd_str = _format_cmd_str(cmd)
    cmd_str_for_display = echo_cmd if echo_cmd is not None else cmd_str
    logger.debug(f"[dry-run] {cmd_str_for_display}", extra={"cwd": cwd})
    return subprocess.CompletedProcess(
        args=cmd,
        returncode=0,
        stdout="" if capture_output else None,
        stderr="" if capture_output else None,
    )


def _cmd_name(cmd_str: str) -> str:
    max_len = 50
    if len(cmd_str) > max_len:
        return cmd_str[: max_len - 3] + "..."
    return cmd_str


def dump_output(result: StrOrNoneCompletedProcess) -> None:
    if result.stdout:
        console.thin_line(style.dim("stdout"))
        console.err.print(Text.from_ansi(result.stdout.rstrip()), highlight=False)
    if result.stderr:
        console.thin_line(style.dim("stderr"))
        console.err.print(Text.from_ansi(result.stderr.rstrip()), highlight=False)


def _check_exit_code(
    result: StrOrNoneCompletedProcess,
    check: bool,
    cmd_str_for_display: str,
    stream: bool = True,
) -> None:
    if check and result.returncode != 0:
        logger.debug(
            f"[error] {cmd_str_for_display}",
            extra={
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
        )
        # Show output if not streamed (user hasn't seen it)
        if not stream:
            if result.stdout or result.stderr:
                dump_output(result)
            else:
                console.error(
                    f"Command {style.code(_cmd_name(cmd_str_for_display))} "
                    f"failed with exit code {result.returncode}"
                )
        raise typer.Exit(result.returncode)


def _process_stream_output(
    splitter: OutputSplitter,
    proc: subprocess.Popen,
    cmd: str | list[str] | tuple[str, ...],
) -> subprocess.CompletedProcess[str]:
    encoding = splitter._encoding or "utf-8"
    stdout = splitter.stdout.decode(encoding, errors="replace")
    stderr = splitter.stderr.decode(encoding, errors="replace")
    # Normalize PTY line endings (\r\n -> \n)
    stdout = stdout.replace("\r\n", "\n")
    stderr = stderr.replace("\r\n", "\n")

    return subprocess.CompletedProcess(
        args=cmd, returncode=proc.returncode, stdout=stdout, stderr=stderr
    )


def _prepare_subprocess_env(env: dict[str, str] | None = None) -> dict[str, str]:
    merged_env = os.environ.copy()
    merged_env.pop(ENV__BAKE_REINVOKED, None)

    if env:
        merged_env.update(env)
    merged_env.setdefault("FORCE_COLOR", "1")
    merged_env.setdefault("CLICOLOR_FORCE", "1")

    # Disable progress indicators for tools that support it
    merged_env.setdefault("UV_NO_PROGRESS", "1")  # uv
    merged_env.setdefault("NPM_CONFIG_PROGRESS", "false")  # npm
    merged_env.setdefault("PIP_PROGRESS_BAR", "off")  # pip
    merged_env.setdefault("CARGO_TERM_PROGRESS_WHEN", "never")  # cargo

    try:
        terminal_size = os.get_terminal_size()
        merged_env.setdefault("COLUMNS", str(terminal_size.columns))  # pragma: no cover
        merged_env.setdefault("LINES", str(terminal_size.lines))  # pragma: no cover
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
            start_new_session=True,
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
            start_new_session=True,
            **kwargs,
        )
        # Attach threads BEFORE releasing lock to ensure reader is ready
        # when fast-exiting processes complete
        splitter = OutputSplitter(stream=True, capture=capture_output, encoding=_encoding)
        threads = splitter.attach(proc)

    return StreamSetup(proc=proc, splitter=splitter, threads=threads)


def _run_with_split(
    cmd: str | list[str] | tuple[str, ...],
    shell: bool,
    cwd: Path | str | None,
    capture_output: bool,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
    _encoding: str | None = None,
    **kwargs,
) -> StrOrNoneCompletedProcess:
    use_pty = sys.platform != "win32" and capture_output

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

    with _sigint_guard(setup.proc):
        try:
            setup.proc.wait(timeout=timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            _kill_process_tree(setup.proc)
            setup.proc.wait()
            setup.splitter.finalize(setup.threads)
            raise

    setup.splitter.finalize(setup.threads)

    return _process_stream_output(splitter=setup.splitter, proc=setup.proc, cmd=cmd)


def _kill_process_tree(proc: subprocess.Popen) -> None:
    """Kill a process and all its children.

    On Unix, sends SIGTERM to the process group (because ``sh -c`` does not
    forward signals to children), then escalates to SIGKILL after 5s.
    On Windows, uses ``taskkill /F /T`` to kill the process tree.
    Idempotent — safe to call on already-dead processes.
    """
    if proc.poll() is not None:
        return

    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True,
                timeout=5,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):  # pragma: no cover
            proc.kill()  # pragma: no cover
    else:
        try:
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            proc.kill()
            return

        try:
            proc.wait(timeout=5)
            return
        except subprocess.TimeoutExpired:
            pass
        except KeyboardInterrupt:
            pass

        try:
            os.killpg(pgid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            proc.kill()


@contextlib.contextmanager
def _sigint_guard(proc: subprocess.Popen):
    """Install SIGINT handler to kill the process tree on Ctrl+C.

    Needed because ``proc.wait()``/``proc.communicate()`` don't reliably
    raise ``KeyboardInterrupt`` when ``capture_output=False``.
    """

    def _on_sigint(signum: int, frame: types.FrameType | None) -> None:
        _ = signum, frame
        _kill_process_tree(proc)
        raise KeyboardInterrupt

    if threading.current_thread() is not threading.main_thread():
        yield
        return

    old_handler = signal.signal(signal.SIGINT, _on_sigint)
    try:
        yield
    finally:
        signal.signal(signal.SIGINT, old_handler)


def _run_without_split(
    cmd: str | list[str] | tuple[str, ...],
    shell: bool,
    cwd: Path | str | None,
    capture_output: bool,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
    _encoding: str | None = None,
    **kwargs,
) -> StrOrNoneCompletedProcess:
    # Prepare environment (merges with system env to preserve SYSTEMROOT on Windows)
    env = _prepare_subprocess_env(env)

    # Use Popen instead of run() for better cleanup control on KeyboardInterrupt
    with _subprocess_create_lock:
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE if capture_output else None,
            stderr=subprocess.PIPE if capture_output else None,
            shell=shell,
            env=env,
            start_new_session=True,
            **kwargs,
        )

    with _sigint_guard(proc):
        try:
            stdout_bytes, stderr_bytes = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            _kill_process_tree(proc)
            proc.wait()
            raise
        except KeyboardInterrupt:
            # SIGINT handler already called _kill_process_tree, just wait for proc.
            proc.wait()
            raise

    # Handle output based on capture_output and encoding
    if capture_output:
        encoding = _encoding or "utf-8"
        # When capture_output=True, we set stdout=PIPE and stderr=PIPE,
        # so communicate() returns bytes
        assert isinstance(stdout_bytes, (bytes, type(None)))
        assert isinstance(stderr_bytes, (bytes, type(None)))
        stdout_bytes_final = stdout_bytes if stdout_bytes is not None else b""
        stderr_bytes_final = stderr_bytes if stderr_bytes is not None else b""
        stdout = stdout_bytes_final.decode(encoding, errors="replace")
        stderr = stderr_bytes_final.decode(encoding, errors="replace")
    else:
        stdout = None
        stderr = None

    return subprocess.CompletedProcess(
        args=cmd,
        returncode=proc.returncode,
        stdout=stdout,
        stderr=stderr,
    )


def _log_completion(
    cmd_str_for_display: str, result: subprocess.CompletedProcess, start: float
) -> None:
    elapsed_seconds = time.perf_counter() - start
    logger.debug(
        f"[done] {cmd_str_for_display}",
        extra={
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "elapsed_seconds": elapsed_seconds,
        },
    )
