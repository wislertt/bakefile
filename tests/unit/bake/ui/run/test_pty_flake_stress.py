"""TEMPORARY CI diagnostic for the macOS PTY empty-capture flake. Delete after diagnosis.

Loops capture variants through run()/run_script() and, on the first lost
payload, fails with the tail of an event trace collected from OutputSplitter.
The trace distinguishes: thread crashed / EIO with zero reads / read but not
captured / timed out.
"""

import fcntl
import os
import struct
import sys
import termios
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from bake.ui.run.main import run
from bake.ui.run.script import run_script
from bake.ui.run.splitter import OutputSplitter

TRACE_PATH = Path("/tmp/pty_trace.log")
ITERATIONS = 20
_pid = str(os.getpid())


def _trace(msg: str) -> None:
    with TRACE_PATH.open("a") as f:
        f.write(f"[{_pid}] {msg}\n")


def _install_instrumentation() -> None:
    _orig_handle = OutputSplitter._handle_data
    _orig_eio_read = OutputSplitter._read_pty_eio_safe
    _orig_read_pty = OutputSplitter._read_pty
    _orig_drain = OutputSplitter._drain_pty

    def handle_data(self: OutputSplitter, data: bytes, target: Any, output_list: list) -> bool:
        result = _orig_handle(self, data, target, output_list)
        _trace(f"handle_data len={len(data)} captured={result} head={data[:32]!r}")
        return result

    def eio_read(self: OutputSplitter, pty_fd: int) -> bytes | None:
        data = _orig_eio_read(self, pty_fd)
        if data is not None:
            _trace(f"read fd={pty_fd} len={len(data)}")
        else:
            _trace(f"read fd={pty_fd} EOF-EIO")
        return data

    def read_pty(
        self: OutputSplitter,
        pty_fd: int,
        target: Any,
        output_list: list,
        proc: Any,
    ) -> None:
        _trace(f"read_pty start fd={pty_fd}")
        try:
            _orig_read_pty(self, pty_fd, target, output_list, proc)
        except BaseException as exc:
            _trace(f"read_pty CRASH fd={pty_fd} {exc!r}")
            raise
        _trace(f"read_pty end fd={pty_fd} captured={len(b''.join(output_list))}")

    def drain(self: OutputSplitter, pty_fd: int, target: Any, output_list: list) -> None:
        _trace(f"drain start fd={pty_fd} have={len(b''.join(output_list))}")
        _orig_drain(self, pty_fd, target, output_list)
        _trace(f"drain end fd={pty_fd} captured={len(b''.join(output_list))}")

    OutputSplitter._handle_data = handle_data  # type: ignore[method-assign]
    OutputSplitter._read_pty_eio_safe = eio_read  # type: ignore[method-assign]
    OutputSplitter._read_pty = read_pty  # type: ignore[method-assign]
    OutputSplitter._drain_pty = drain  # type: ignore[method-assign]

    def excepthook(args: threading.ExceptHookArgs) -> None:
        thread_name = args.thread.name if args.thread is not None else "?"
        _trace(f"THREAD CRASH {thread_name}: {args.exc_value!r}")

    threading.excepthook = excepthook


_install_instrumentation()


def _trace_tail(lines: int = 120) -> str:
    if not TRACE_PATH.exists():
        return "<no trace>"
    return "\n".join(TRACE_PATH.read_text().splitlines()[-lines:])


def _loop(name: str, body: Callable[[], None]) -> None:
    for i in range(ITERATIONS):
        _trace(f"ITER {name} #{i} begin pid={_pid}")
        try:
            body()
        except AssertionError:
            pytest.fail(f"{name} iter {i} lost payload\n--- trace tail ---\n{_trace_tail()}")


def test_stress_stdout_capture() -> None:
    def body() -> None:
        result = run(
            [sys.executable, "-c", "print('MARKER-STDOUT')"], capture_output=True, echo=False
        )
        assert "MARKER-STDOUT" in (result.stdout or "")

    _loop("stdout", body)


def test_stress_stderr_stream_capture() -> None:
    def body() -> None:
        child = "import sys; sys.stderr.write('MARKER-STDERR\\n')"
        result = run([sys.executable, "-c", child], stream=True, capture_output=True, echo=False)
        assert "MARKER-STDERR" in (result.stderr or "")

    _loop("stderr", body)


def test_stress_run_script() -> None:
    def body() -> None:
        result = run_script("stress", "echo MARKER-SCRIPT", echo=False)
        assert "MARKER-SCRIPT" in (result.stdout or "")

    _loop("script", body)


_WINSIZE_CHILD = r"""
import fcntl, struct, sys, termios

ws = fcntl.ioctl(1, termios.TIOCGWINSZ, b"\x00" * 8)
rows, cols = struct.unpack("HHHH", ws)[:2]
print(f"{cols}x{rows}")
"""


def test_stress_winsize(monkeypatch: pytest.MonkeyPatch) -> None:
    parent_ws = struct.pack("HHHH", 30, 100, 0, 0)
    real_ioctl = fcntl.ioctl

    def fake_ioctl(fd: int, request: int, buf: Any = None) -> Any:
        if request == termios.TIOCGWINSZ:
            return parent_ws
        if buf is None:
            return real_ioctl(fd, request)
        return real_ioctl(fd, request, buf)

    def body() -> None:
        with monkeypatch.context() as m:
            m.setattr(fcntl, "ioctl", fake_ioctl)
            result = run([sys.executable, "-c", _WINSIZE_CHILD], capture_output=True, echo=False)
        assert "100x30" in (result.stdout or "")

    _loop("winsize", body)
