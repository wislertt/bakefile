import os
import select
import subprocess
import sys
import threading


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

    def _read_pty(self, pty_fd: int, target, output_list, proc: subprocess.Popen):
        """Read from PTY file descriptor in chunks and stream to output."""
        while True:
            # Wait for data to be available or process to exit
            ready, _, _ = select.select([pty_fd], [], [], 0.1)

            if ready:
                try:
                    data = os.read(pty_fd, 4096)
                    if not data:
                        break
                    if self._stream:
                        target.buffer.write(data)
                        target.buffer.flush()
                    if self._capture:
                        output_list.append(data)
                except OSError:
                    break

            # Check if process has exited
            if proc.poll() is not None:
                # Process ended, do one final read to get any remaining data
                try:
                    while True:
                        data = os.read(pty_fd, 4096)
                        if not data:
                            break
                        if self._stream:
                            target.buffer.write(data)
                            target.buffer.flush()
                        if self._capture:
                            output_list.append(data)
                except OSError:
                    pass
                break

        os.close(pty_fd)

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
