import os
import select
import subprocess
import sys
import threading
import time

# Module-level lock for PTY streaming operations to prevent race conditions
# when multiple threads run commands concurrently with PTY-based output capture.
_pty_stream_lock = threading.Lock()


class OutputSplitter:
    def __init__(self, stream: bool = True, capture: bool = True, pty_fd: int | None = None):
        self._stream = stream
        self._capture = capture
        self._pty_fd = pty_fd
        self._stdout_data = b""
        self._stderr_data = b""

    def _read_stream(self, stream, target, output_list):
        for line in iter(stream.readline, b""):
            if self._stream:
                target.buffer.write(line)
                target.buffer.flush()
            if self._capture:
                output_list.append(line)
        stream.close()

    def _handle_data(self, data: bytes, target, output_list) -> bool:
        """Handle data chunk: return False if data is empty (EOF)."""
        if not data:
            return False
        if self._stream:
            target.buffer.write(data)
            target.buffer.flush()
        if self._capture:
            output_list.append(data)
        return True

    def _read_pty(self, pty_fd: int, target, output_list, proc: subprocess.Popen):
        """Read from PTY file descriptor in chunks and stream to output."""
        try:
            while True:
                # Wait for data to be available (without lock - allows concurrent waiting)
                ready, _, _ = select.select([pty_fd], [], [], 0.1)

                if ready:
                    # Lock only protects the actual read operation
                    with _pty_stream_lock:
                        if not self._read_pty_data(pty_fd, target, output_list):
                            break

                if proc.poll() is not None:
                    # Process exited, drain remaining data with lock protection
                    with _pty_stream_lock:
                        self._drain_pty(pty_fd, target, output_list)
                    break
        finally:
            # Close PTY fd with lock protection
            with _pty_stream_lock:
                os.close(pty_fd)

    def _read_pty_data(self, pty_fd: int, target, output_list) -> bool:
        """Read and handle available PTY data. Returns False on EOF/error."""
        try:
            data = os.read(pty_fd, 4096)
            return self._handle_data(data, target, output_list)
        except OSError:
            return False

    def _drain_pty(self, pty_fd: int, target, output_list):
        """Drain remaining data from PTY after process exits.

        With the PTY lock preventing concurrent thread interference, we still need
        to handle OS timing: proc.poll() may return exit code before the PTY buffer
        is fully flushed. We use select to wait for data with increasing timeouts,
        and also try direct reads as a fallback in case select doesn't detect
        readiness (e.g., in tests with mocked os.read).
        """
        # DEBUG: Track entry
        import sys as _sys
        import traceback as _tb

        print(
            f"[_drain_pty] ENTRY: pty_fd={pty_fd}, target={target}, output_list={output_list}",
            file=_sys.stderr,
        )

        # Give OS a moment to flush the PTY buffer
        time.sleep(0.005)

        timeout = 0.05  # Start at 50ms
        consecutive_timeouts = 0
        max_timeouts = 4  # Allow up to 4 consecutive timeouts
        iteration = 0
        select_works = True  # Track if select.select() works (fails on Windows with non-socket fds)

        try:
            while consecutive_timeouts < max_timeouts:
                iteration += 1
                print(
                    f"[_drain_pty] Iteration {iteration}: consecutive_timeouts={consecutive_timeouts}, timeout={timeout}",
                    file=_sys.stderr,
                )

                # Try to use select.select() if it worked before
                if select_works:
                    try:
                        ready, _, _ = select.select([pty_fd], [], [], timeout)
                        print(f"[_drain_pty] select.select returned: ready={ready}", file=_sys.stderr)
                    except OSError as e:
                        # On Windows, select.select() raises OSError for non-socket file descriptors
                        print(f"[_drain_pty] select.select() failed with OSError: {e}, falling back to direct-only mode", file=_sys.stderr)
                        select_works = False
                        ready = False
                else:
                    ready = False

                if ready:
                    # select says data is ready, read it
                    print(
                        f"[_drain_pty] Data ready, calling os.read({pty_fd}, 4096)",
                        file=_sys.stderr,
                    )
                    data = os.read(pty_fd, 4096)
                    print(f"[_drain_pty] os.read returned: {data!r}", file=_sys.stderr)

                    handled = self._handle_data(data, target, output_list)
                    print(
                        f"[_drain_pty] _handle_data returned: {handled}, output_list now: {output_list}",
                        file=_sys.stderr,
                    )

                    if not handled:
                        # EOF or error, done draining
                        print("[_drain_pty] EOF detected, returning", file=_sys.stderr)
                        return
                    # Got data, reset counters and reduce timeout
                    consecutive_timeouts = 0
                    timeout = 0.02
                else:
                    # select timed out or select doesn't work
                    if select_works:
                        print("[_drain_pty] select timed out", file=_sys.stderr)
                        consecutive_timeouts += 1
                    else:
                        print("[_drain_pty] In direct-only mode (select doesn't work)", file=_sys.stderr)

                    timeout = min(timeout * 1.5, 0.2)  # Max 200ms

                    # After 2 consecutive timeouts (or immediately in direct-only mode), try direct read
                    # This handles cases where select doesn't detect readiness properly
                    # (e.g., mocked os.read in tests, or certain PTY states, or Windows with non-socket fds)
                    if not select_works or consecutive_timeouts >= 2:
                        print("[_drain_pty] Trying direct read (fallback)", file=_sys.stderr)
                        data = os.read(pty_fd, 4096)
                        print(f"[_drain_pty] Direct os.read returned: {data!r}", file=_sys.stderr)

                        handled = self._handle_data(data, target, output_list)
                        print(
                            f"[_drain_pty] _handle_data returned: {handled}, output_list now: {output_list}",
                            file=_sys.stderr,
                        )

                        if not handled:
                            # EOF or error
                            print("[_drain_pty] EOF from direct read, returning", file=_sys.stderr)
                            return
                        # If we got data, reset timeout counter and continue
                        if data:
                            print(
                                "[_drain_pty] Got data from direct read, resetting consecutive_timeouts",
                                file=_sys.stderr,
                            )
                            consecutive_timeouts = 0
                        else:
                            print("[_drain_pty] Direct read returned empty data", file=_sys.stderr)
                        # else: empty read but not EOF, keep trying (incremented above)
            print(
                f"[_drain_pty] Loop ended: consecutive_timeouts={consecutive_timeouts} >= max_timeouts={max_timeouts}",
                file=_sys.stderr,
            )
        except OSError as e:
            # Catch any other OSErrors (e.g., from os.read)
            print(f"[_drain_pty] OSError caught: {e}", file=_sys.stderr)
            print("[_drain_pty] Traceback:", file=_sys.stderr)
            _tb.print_exc()
            print()

        print(f"[_drain_pty] EXIT: output_list={output_list}", file=_sys.stderr)

    def attach(self, proc: subprocess.Popen):
        threads = []

        # Handle PTY stdout (for color-preserving output on Unix)
        if self._pty_fd is not None:
            stdout_list = []
            t = threading.Thread(
                target=self._read_pty, args=(self._pty_fd, sys.stdout, stdout_list, proc)
            )
            t.daemon = True
            t.start()
            threads.append((t, stdout_list, "stdout"))

        # Handle regular stdout
        elif proc.stdout:
            stdout_list = []
            t = threading.Thread(
                target=self._read_stream, args=(proc.stdout, sys.stdout, stdout_list)
            )
            t.daemon = True
            t.start()
            threads.append((t, stdout_list, "stdout"))

        # Handle stderr (regular pipe)
        if proc.stderr:
            stderr_list = []
            t = threading.Thread(
                target=self._read_stream, args=(proc.stderr, sys.stderr, stderr_list)
            )
            t.daemon = True
            t.start()
            threads.append((t, stderr_list, "stderr"))

        return threads

    def finalize(self, threads):
        for t, data_list, name in threads:
            t.join()
            if name == "stdout":
                self._stdout_data = b"".join(data_list)
            else:
                self._stderr_data = b"".join(data_list)

    @property
    def stdout(self) -> bytes:
        return self._stdout_data

    @property
    def stderr(self) -> bytes:
        return self._stderr_data
