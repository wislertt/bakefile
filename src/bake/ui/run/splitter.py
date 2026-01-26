import errno
import os
import select
import subprocess
import sys
import threading
import time

# No PTY locks needed - each thread reads from its own PTY fd independently
# Locks were causing race conditions where threads waited while their process exited


class OutputSplitter:
    def __init__(
        self,
        stream: bool = True,
        capture: bool = True,
        pty_fd: int | None = None,
        stderr_pty_fd: int | None = None,
        encoding: str | None = None,
    ):
        self._stream = stream
        self._capture = capture
        self._pty_fd = pty_fd
        self._stderr_pty_fd = stderr_pty_fd
        self._encoding = encoding
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

    def _read_pty_eio_safe(self, pty_fd: int) -> bytes | None:
        """Read from PTY, treating EIO as EOF (returns None)."""
        try:
            return os.read(pty_fd, 4096)
        except OSError as e:
            if e.errno == errno.EIO:
                return None
            raise

    def _try_immediate_read(self, pty_fd: int, target, output_list) -> bool:
        """Try immediate non-blocking read. Returns True if should continue."""
        import fcntl

        flags = fcntl.fcntl(pty_fd, fcntl.F_GETFL)
        fcntl.fcntl(pty_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        data = self._read_pty_eio_safe(pty_fd)
        if data is None or not self._handle_data(data, target, output_list):
            fcntl.fcntl(pty_fd, fcntl.F_SETFL, flags)
            return False

        fcntl.fcntl(pty_fd, fcntl.F_SETFL, flags)
        return True

    def _blocking_pty_read(self, pty_fd: int, target, output_list) -> bool:
        """Try select-based blocking read. Returns True if should continue."""
        import fcntl

        flags = fcntl.fcntl(pty_fd, fcntl.F_GETFL)
        fcntl.fcntl(pty_fd, fcntl.F_SETFL, flags)

        ready, _, _ = select.select([pty_fd], [], [], 0.1)
        if ready:
            data = self._read_pty_eio_safe(pty_fd)
            if data is None or not self._handle_data(data, target, output_list):
                return False
        return True

    def _read_pty(self, pty_fd: int, target, output_list, proc: subprocess.Popen):
        """Read from PTY file descriptor in chunks and stream to output."""
        try:
            while True:
                try:
                    if not self._try_immediate_read(pty_fd, target, output_list):
                        break
                except BlockingIOError:
                    if not self._blocking_pty_read(pty_fd, target, output_list):
                        break

                if proc.poll() is not None:
                    self._drain_pty(pty_fd, target, output_list)
                    break
        finally:
            os.close(pty_fd)

    def _read_pty_data(self, pty_fd: int, target, output_list) -> bool:
        """Read and handle available PTY data. Returns False on EOF/error."""
        try:
            data = os.read(pty_fd, 4096)
            return self._handle_data(data, target, output_list)
        except OSError:
            return False

    def _try_select_read(self, pty_fd: int, timeout: float) -> tuple[bool, bool]:
        """Try to read using select.select().

        Returns:
            (success, has_data): success if select worked, has_data if ready
        """
        try:
            ready, _, _ = select.select([pty_fd], [], [], timeout)
            return True, bool(ready)
        except OSError:
            # On Windows, select.select() raises OSError for non-socket file descriptors
            return False, False

    def _read_and_handle(self, pty_fd: int, target, output_list) -> bool:
        """Read from PTY and handle data.

        Returns:
            True if data was handled, False if EOF/error
        """
        try:
            data = os.read(pty_fd, 4096)
            return self._handle_data(data, target, output_list)
        except OSError:
            return False

    def _handle_data_ready(self, pty_fd: int, target, output_list) -> bool:
        """Handle data ready from select.

        Returns:
            True if should continue draining, False if done
        """
        return self._read_and_handle(pty_fd, target, output_list)

    def _handle_timeout(
        self,
        pty_fd: int,
        target,
        output_list,
        select_works: bool,
        consecutive_timeouts: int,
    ) -> tuple[bool, int]:
        """Handle timeout when no data ready.

        Returns:
            (should_continue, new_timeout_count)
        """
        # Try direct read after 2 consecutive timeouts or if select doesn't work
        if not select_works or consecutive_timeouts >= 2:
            if not self._read_and_handle(pty_fd, target, output_list):
                return False, 0
            return True, 0  # Got data, reset timeout counter
        return True, consecutive_timeouts + 1

    def _drain_pty(self, pty_fd: int, target, output_list):
        """Drain remaining data from PTY after process exits.

        We need to handle OS timing: proc.poll() may return exit code before the
        PTY buffer is fully flushed. We use select to wait for data with increasing
        timeouts, and also try direct reads as a fallback in case select doesn't
        detect readiness (e.g., in tests with mocked os.read or on Windows with
        non-socket file descriptors).
        """
        time.sleep(0.005)

        timeout = 0.05
        consecutive_timeouts = 0
        max_timeouts = 4
        select_works = True

        try:
            while consecutive_timeouts < max_timeouts:
                # Check if data is ready via select
                if select_works:
                    select_works, ready = self._try_select_read(pty_fd, timeout)
                else:
                    ready = False

                if ready:
                    # Data ready - read and handle
                    if not self._handle_data_ready(pty_fd, target, output_list):
                        return
                    consecutive_timeouts = 0
                    timeout = 0.02
                    continue

                # No data ready - increment timeout and try direct read
                timeout = min(timeout * 1.5, 0.2)

                should_continue, consecutive_timeouts = self._handle_timeout(
                    pty_fd, target, output_list, select_works, consecutive_timeouts
                )
                if not should_continue:
                    return
        except OSError:
            pass

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

        # Handle PTY stderr (for color-preserving stderr on Unix)
        if self._stderr_pty_fd is not None:
            stderr_list = []
            t = threading.Thread(
                target=self._read_pty, args=(self._stderr_pty_fd, sys.stderr, stderr_list, proc)
            )
            t.daemon = True
            t.start()
            threads.append((t, stderr_list, "stderr"))

        # Handle stderr (regular pipe) - use separate if, not elif
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
