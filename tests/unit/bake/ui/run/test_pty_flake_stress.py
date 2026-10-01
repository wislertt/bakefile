"""TEMPORARY CI diagnostic for the macOS PTY empty-capture flake.

Delete with the ci/pty-flake-repro branch. Loops capture variants through
run()/run_script(); on the first lost payload, fails with the tail of the
event trace from tests/utils/pty_trace.py.
"""

import fcntl
import os
import struct
import sys
import termios
from collections.abc import Callable
from typing import Any

import pytest

from bake.ui.run.main import run
from bake.ui.run.script import run_script
from tests.utils.pty_trace import trace, trace_tail

TRACE_PATH = os.environ.get("PTY_TRACE_PATH", "/tmp/pty_trace.log")
ITERATIONS = 20


def _loop(name: str, body: Callable[[], None]) -> None:
    for i in range(ITERATIONS):
        trace(f"ITER {name} #{i} begin pid={os.getpid()}")
        try:
            body()
        except AssertionError:
            pytest.fail(f"{name} iter {i} lost payload\n--- trace tail ---\n{trace_tail()}")


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
