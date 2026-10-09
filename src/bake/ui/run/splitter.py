import contextlib
import ctypes
import errno
import os
import select
import subprocess
import sys
import threading
import time

# No PTY locks needed - each thread reads from its own PTY fd independently
# Locks were causing race conditions where threads waited while their process exited

_READ_CHUNK = 4096  # tty line discipline delivers ~4KB per read regardless of ask

if sys.platform == "darwin":
    _libc = ctypes.CDLL(None, use_errno=True)
    _SZOMB = 5  # sys/proc.h: p_stat value for a zombie
    _P_WEXIT = 0x2000  # p_flag: process is working on exiting


def _process_is_exiting(pid: int) -> bool:
    """Read the child's kinfo_proc via sysctl without touching it.

    P_WEXIT is set inside exit1(), after the child's last userspace write but
    ~0.6s before the session-leader exit processing that discards unread PTY
    master data on macOS. SZOMB covers the final transition. Any wait syscall
    (waitpid, waitid, poll) that observes the child reapable triggers that
    teardown, so reader threads must never poll() the child on darwin.
    """
    mib = (ctypes.c_int * 4)(1, 14, 1, pid)  # CTL_KERN, KERN_PROC, KERN_PROC_PID
    buf = ctypes.create_string_buffer(1024)
    size = ctypes.c_size_t(1024)
    if _libc.sysctl(mib, 4, buf, ctypes.byref(size), None, 0) != 0:
        err = ctypes.get_errno()
        if err == errno.ESRCH:
            return True  # pid gone: nothing to wait for
        raise OSError(err, os.strerror(err))
    if size.value == 0:  # pid gone: already reaped or never existed
        return True
    # struct extern_proc: p_flag int @32, p_stat char @36, p_pid int @40
    assert int.from_bytes(buf.raw[40:44], "little") == pid  # layout guard
    return buf.raw[36] == _SZOMB or bool(int.from_bytes(buf.raw[32:36], "little") & _P_WEXIT)


def _reader_should_drain(proc: subprocess.Popen) -> bool:
    """True when the child is done and the reader should drain its master fd.

    poll() is a wait syscall: on darwin the call that observes the child
    reapable discards unread PTY master data, so the reader checks process
    state via sysctl instead. Other platforms never discard on reap.
    """
    if sys.platform == "darwin":
        return _process_is_exiting(proc.pid)
    return proc.poll() is not None


class OutputSplitter:
    def __init__(
        self,
        stream: bool = True,
        capture: bool = True,
        pty_fd: int | None = None,
        stderr_pty_fd: int | None = None,
        encoding: str | None = None,
        drain_timeout: float | None = 10.0,
    ):
        self._stream = stream
        self._capture = capture
        self._pty_fd = pty_fd
        self._stderr_pty_fd = stderr_pty_fd
        self._encoding = encoding
        self._drain_timeout = drain_timeout
        self._pty_locks: dict[int, threading.Lock] = {}
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

    def _fd_lock(self, pty_fd: int) -> threading.Lock:
        """Per-fd lock serializing read+handle between consumers.

        The reader thread and rescue_pending may both drain the same
        master fd. A read by one and a read by the other can complete in
        opposite order to how the chunks are then appended to the capture
        (seen in CI as a JSON doc whose tail preceded its head). Holding
        the lock across read+handle makes each chunk append in kernel
        FIFO order regardless of which consumer wins the race.
        """
        lock = self._pty_locks.get(pty_fd)
        if lock is None:
            lock = threading.Lock()
            self._pty_locks[pty_fd] = lock
        return lock

    def _read_pty_eio_safe(self, pty_fd: int) -> bytes | None:
        """Read from PTY, treating EIO as EOF (returns None)."""
        try:
            return os.read(pty_fd, _READ_CHUNK)
        except OSError as e:
            if e.errno == errno.EIO:
                return None
            raise

    def _try_immediate_read(self, pty_fd: int, target, output_list) -> bool:
        """Try immediate non-blocking read. Returns True if should continue."""
        import fcntl

        flags = fcntl.fcntl(pty_fd, fcntl.F_GETFL)
        fcntl.fcntl(pty_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        try:
            with self._fd_lock(pty_fd):
                data = self._read_pty_eio_safe(pty_fd)
                return not (data is None or not self._handle_data(data, target, output_list))
        finally:
            # Restore on EAGAIN too: a leaked O_NONBLOCK makes drain misread EAGAIN as EOF
            fcntl.fcntl(pty_fd, fcntl.F_SETFL, flags)

    def _blocking_pty_read(self, pty_fd: int, target, output_list) -> bool:
        """Try select-based blocking read. Returns True if should continue."""
        import fcntl

        flags = fcntl.fcntl(pty_fd, fcntl.F_GETFL)
        fcntl.fcntl(pty_fd, fcntl.F_SETFL, flags)

        ready, _, _ = select.select([pty_fd], [], [], 0.1)
        if ready:
            with self._fd_lock(pty_fd):
                try:
                    data = self._read_pty_eio_safe(pty_fd)
                except BlockingIOError:
                    # Another consumer drained the ready chunk first
                    return True
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

                if _reader_should_drain(proc):
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
            True if data was handled (or EAGAIN - no data yet), False if EOF/error
        """
        try:
            with self._fd_lock(pty_fd):
                data = os.read(pty_fd, _READ_CHUNK)
                return self._handle_data(data, target, output_list)
        except BlockingIOError:
            return True
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
        # Probe only where select is unusable: a direct read can block past the drain deadline
        if not select_works:
            if not self._read_and_handle(pty_fd, target, output_list):
                return False, 0
            return True, 0  # Got data, reset timeout counter
        return True, consecutive_timeouts + 1

    def _drain_pty(self, pty_fd: int, target, output_list):
        """Drain remaining PTY data after the main process exits.

        Master EOF (EIO) only arrives once every slave fd closes, grandchildren
        included, so draining to EOF matches pipe semantics. drain_timeout caps
        the wait (None = forever, subprocess parity).
        """
        time.sleep(0.005)

        deadline = None if self._drain_timeout is None else time.monotonic() + self._drain_timeout

        with contextlib.suppress(OSError):  # pragma: no cover
            self._drain_loop(pty_fd, target, output_list, deadline)

    def _past_deadline(self, deadline: float | None) -> bool:
        return deadline is not None and time.monotonic() >= deadline

    def _drain_loop(self, pty_fd: int, target, output_list, deadline: float | None) -> None:
        timeout = 0.05
        consecutive_timeouts = 0
        select_works = True

        while not self._past_deadline(deadline):
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

    def rescue_pending(self, master_fds, threads) -> None:
        """Recover pending master data immediately after the child exits.

        macOS discards unread PTY master data when the session leader is
        reaped, and reader threads may not have consumed it yet under CPU
        contention. Drain from the calling thread here, before finalize joins
        the readers. Data already read by a racing reader is not duplicated
        (the kernel queue is consumed once).
        """
        # Reader threads may still be draining this fd: two consumers
        # appending chunks in whichever order their reads complete can
        # reorder the capture (seen in CI as a JSON doc whose tail
        # preceded its head). _fd_lock serializes read+handle per fd.
        for pty_fd, (_, output_list, name) in zip(master_fds, threads, strict=True):
            target = sys.stdout if name == "stdout" else sys.stderr
            while True:
                # select inside the lock: with it held, a ready fd is
                # guaranteed to still have the selected chunk on read
                with self._fd_lock(pty_fd):
                    select_works, ready = self._try_select_read(pty_fd, 0.02)
                    if not select_works or not ready:
                        break
                    try:
                        data = os.read(pty_fd, _READ_CHUNK)
                    except OSError:
                        break
                    if not self._handle_data(data, target, output_list):
                        break

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
        elif proc.stdout and hasattr(proc.stdout, "readline"):
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
        if proc.stderr and hasattr(proc.stderr, "readline"):
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
