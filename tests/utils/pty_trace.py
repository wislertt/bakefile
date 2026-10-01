"""TEMPORARY PTY capture instrumentation for flake diagnosis.

Delete with the ci/pty-flake-repro branch. Activated by env PTY_TRACE=1
(tests/conftest.py installs into OutputSplitter + run()).
"""

import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, cast

import bake.ui.run.main  # noqa: F401
from bake.ui.run.splitter import OutputSplitter

run_main = sys.modules["bake.ui.run.main"]

TRACE_PATH = Path("/tmp/pty_trace.log")
_pid = os.getpid()
_installed = False
_run_seq = 0


def trace(msg: str) -> None:
    with TRACE_PATH.open("a") as f:
        f.write(f"[{_pid}] {time.monotonic():.3f} {msg}\n")


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
    _orig_process = run_main._process_stream_output
    _orig_split = run_main._run_with_split

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

    def process_stream_output(splitter, proc, cmd, **kwargs):
        result = _orig_process(splitter, proc, cmd, **kwargs)
        trace(
            f"PROCESS cmd={cmd!r} raw_out={len(splitter.stdout)} "
            f"raw_err={len(splitter.stderr)} final_out={len(result.stdout or '')} "
            f"rc={result.returncode}"
        )
        return result

    def run_with_split(*args, **kwargs):
        global _run_seq
        _run_seq += 1
        seq = _run_seq
        cmd = args[0] if args else kwargs.get("cmd")
        trace(f"RUN #{seq} begin cmd={cmd!r}")
        result = _orig_split(*args, **kwargs)
        out = result.stdout if hasattr(result, "stdout") else None
        trace(f"RUN #{seq} end rc={result.returncode} out={len(out) if out else 0}")
        return result

    OutputSplitter._handle_data = handle_data  # type: ignore[method-assign]
    OutputSplitter._read_pty_eio_safe = eio_read  # type: ignore[method-assign]
    OutputSplitter._read_pty = read_pty  # type: ignore[method-assign]
    OutputSplitter._drain_pty = drain  # type: ignore[method-assign]
    cast_any = cast("Any", run_main)
    cast_any._process_stream_output = process_stream_output
    cast_any._run_with_split = run_with_split

    def excepthook(args):
        thread_name = args.thread.name if args.thread is not None else "?"
        trace(f"THREAD CRASH {thread_name}: {args.exc_value!r}")

    threading.excepthook = excepthook
