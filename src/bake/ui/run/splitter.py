import os
import select
import subprocess
import sys
import threading

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
        with _pty_stream_lock:  # Lock for entire PTY read operation to prevent race conditions
            while True:
                # Wait for data to be available or process to exit
                ready, _, _ = select.select([pty_fd], [], [], 0.1)

                if ready and not self._read_pty_data(pty_fd, target, output_list):
                    break

                if proc.poll() is not None:
                    self._drain_pty(pty_fd, target, output_list)
                    break

            os.close(pty_fd)

    def _read_pty_data(self, pty_fd: int, target, output_list) -> bool:
        """Read and handle available PTY data. Returns False on EOF/error."""
        try:
            data = os.read(pty_fd, 4096)
            return self._handle_data(data, target, output_list)
        except OSError:
            return False

    def _drain_pty(self, pty_fd: int, target, output_list):
        """Drain remaining data from PTY after process exits."""
        # With the PTY lock in place, concurrent operations are serialized.
        # Use select with small timeout to wait for any remaining data without
        # blocking indefinitely.
        try:
            consecutive_empty_reads = 0
            max_empty_reads = 3  # Tolerate a few empty reads before giving up

            while consecutive_empty_reads < max_empty_reads:
                ready, _, _ = select.select([pty_fd], [], [], 0.05)
                if ready:
                    data = os.read(pty_fd, 4096)
                    if not self._handle_data(data, target, output_list):
                        break
                    consecutive_empty_reads = 0
                else:
                    consecutive_empty_reads += 1
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
