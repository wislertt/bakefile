"""TEMPORARY PTY capture instrumentation for flake diagnosis.

Delete with the ci/pty-flake-repro branch. Activated by env PTY_TRACE=1
(tests/conftest.py installs into OutputSplitter). The trace distinguishes
loss modes: thread crash / EIO with zero reads / read but not captured /
drain timeout.
"""

import os
import threading
from pathlib import Path

from bake.ui.run.splitter import OutputSplitter

TRACE_PATH = Path("/tmp/pty_trace.log")
_pid = os.getpid()
_installed = False


def trace(msg: str) -> None:
    with TRACE_PATH.open("a") as f:
        f.write(f"[{_pid}] {msg}\n")


def trace_tail(lines: int = 120) -> str:
    if not TRACE_PATH.exists():
        return "<no trace>"
    return "\n".join(TRACE_PATH.read_text().splitlines()[-lines:])


def install_pty_trace() -> None:
    global _installed
    if _installed:
        return
    _installed = True

    _orig_handle = OutputSplitter._handle_data
    _orig_eio_read = OutputSplitter._read_pty_eio_safe
    _orig_read_pty = OutputSplitter._read_pty
    _orig_drain = OutputSplitter._drain_pty

    def handle_data(self, data, target, output_list):
        result = _orig_handle(self, data, target, output_list)
        trace(f"handle_data len={len(data)} captured={result} head={data[:32]!r}")
        return result

    def eio_read(self, pty_fd):
        data = _orig_eio_read(self, pty_fd)
        if data is None:
            trace(f"read fd={pty_fd} EOF-EIO")
        else:
            trace(f"read fd={pty_fd} len={len(data)}")
        return data

    def read_pty(self, pty_fd, target, output_list, proc):
        trace(f"read_pty start fd={pty_fd}")
        try:
            _orig_read_pty(self, pty_fd, target, output_list, proc)
        except BaseException as exc:
            trace(f"read_pty CRASH fd={pty_fd} {exc!r}")
            raise
        trace(f"read_pty end fd={pty_fd} captured={len(b''.join(output_list))}")

    def drain(self, pty_fd, target, output_list):
        trace(f"drain start fd={pty_fd} have={len(b''.join(output_list))}")
        _orig_drain(self, pty_fd, target, output_list)
        trace(f"drain end fd={pty_fd} captured={len(b''.join(output_list))}")

    OutputSplitter._handle_data = handle_data  # type: ignore[method-assign]
    OutputSplitter._read_pty_eio_safe = eio_read  # type: ignore[method-assign]
    OutputSplitter._read_pty = read_pty  # type: ignore[method-assign]
    OutputSplitter._drain_pty = drain  # type: ignore[method-assign]

    def excepthook(args):
        thread_name = args.thread.name if args.thread is not None else "?"
        trace(f"THREAD CRASH {thread_name}: {args.exc_value!r}")

    threading.excepthook = excepthook
