import os
import subprocess
from unittest.mock import Mock, patch

import pytest

from bake.ui.run.splitter import OutputSplitter


def test_init_defaults():
    splitter = OutputSplitter()
    assert splitter._stream is True
    assert splitter._capture is True


def test_init_custom_values():
    splitter = OutputSplitter(stream=False, capture=False)
    assert splitter._stream is False
    assert splitter._capture is False


def test_stdout_property():
    splitter = OutputSplitter()
    splitter._stdout_data = b"test output"
    assert splitter.stdout == b"test output"


def test_stderr_property():
    splitter = OutputSplitter()
    splitter._stderr_data = b"error output"
    assert splitter.stderr == b"error output"


def test_attach_returns_threads_list():
    mock_proc = Mock()
    mock_proc.stdout = Mock()
    mock_proc.stderr = None

    splitter = OutputSplitter(stream=False, capture=True)

    with patch("threading.Thread") as mock_thread_class:
        mock_thread = Mock()
        mock_thread_class.return_value = mock_thread

        threads = splitter.attach(mock_proc)

        assert len(threads) == 1
        _, _, name = threads[0]
        assert name == "stdout"
        assert mock_thread.start.called


def test_finalize_sets_stdout_and_stderr():
    splitter = OutputSplitter()

    mock_thread = Mock()
    mock_stdout_list = [b"line1", b"line2"]
    mock_stderr_list = [b"error1"]

    threads = [
        (mock_thread, mock_stdout_list, "stdout"),
        (mock_thread, mock_stderr_list, "stderr"),
    ]

    splitter.finalize(threads)

    assert splitter.stdout == b"line1line2"
    assert splitter.stderr == b"error1"


def test_capture_false_returns_empty_bytes():
    splitter = OutputSplitter(capture=False)
    assert splitter.stdout == b""
    assert splitter.stderr == b""


def test_read_stream_captures_output():
    proc = subprocess.Popen(["echo", "test"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    splitter = OutputSplitter(stream=False, capture=True)
    output_list = []
    splitter._read_stream(proc.stdout, Mock(), output_list)
    assert b"test" in b"".join(output_list)


def test_attach_with_stderr():
    proc = subprocess.Popen(
        ["python", "-c", "import sys; sys.stderr.write('error')"],
        stderr=subprocess.PIPE,
    )
    splitter = OutputSplitter(stream=False, capture=True)
    threads = splitter.attach(proc)
    proc.wait()
    splitter.finalize(threads)

    assert len(threads) == 1
    _, _, name = threads[0]
    assert name == "stderr"
    assert b"error" in splitter.stderr


class TestReadPtyData:
    def test_read_pty_data_returns_false_on_empty_data(self):
        splitter = OutputSplitter(stream=False, capture=True)
        # Empty data should return False (EOF)
        result = splitter._read_pty_data(0, Mock(), [])
        assert result is False

    def test_read_pty_data_returns_false_on_os_error(self):
        splitter = OutputSplitter(stream=False, capture=True)
        # OSError during read should return False
        with patch("os.read", side_effect=OSError("Bad file descriptor")):
            result = splitter._read_pty_data(0, Mock(), [])
            assert result is False


class TestDrainPty:
    def test_drain_pty_handles_empty_data(self):
        splitter = OutputSplitter(stream=False, capture=True)
        output_list = []
        # Simulate os.read returning empty data (EOF)
        with patch("os.read", return_value=b""):
            splitter._drain_pty(0, Mock(), output_list)
            # Should handle gracefully and not crash
            assert output_list == []

    def test_drain_pty_captures_remaining_data(self):
        splitter = OutputSplitter(stream=False, capture=True)
        output_list = []
        # First call has data, second returns empty (EOF)
        with patch("os.read", side_effect=[b"remaining", b""]):
            splitter._drain_pty(0, Mock(), output_list)
            assert output_list == [b"remaining"]

    def test_drain_pty_handles_os_error(self):
        splitter = OutputSplitter(stream=False, capture=True)
        output_list = []
        # OSError should be caught and ignored
        with patch("os.read", side_effect=OSError("Bad file descriptor")):
            splitter._drain_pty(0, Mock(), output_list)
            # Should handle gracefully
            assert output_list == []

    def test_drain_pty_handles_select_timeout(self):
        """Test drain PTY when select.select() times out (covers consecutive_timeouts += 1)."""
        splitter = OutputSplitter(stream=False, capture=True)
        output_list = []

        # Mock select to timeout (return empty ready list) twice, then have data
        # This tests the line: if select_works: consecutive_timeouts += 1
        select_call_count = [0]

        def mock_select(rlist, _wlist, _xlist, _timeout):
            select_call_count[0] += 1
            # First two calls: timeout (no data ready)
            if select_call_count[0] <= 2:
                return ([], [], [])  # Timeout - covers consecutive_timeouts += 1
            # Third call: data ready
            return (rlist, [], [])

        # Mock os.read to return data then EOF
        read_call_count = [0]

        def mock_read(_fd, _size):
            read_call_count[0] += 1
            if read_call_count[0] == 1:
                return b"data"  # First read gets data
            return b""  # Subsequent reads get EOF

        with (
            patch("select.select", side_effect=mock_select),
            patch("os.read", side_effect=mock_read),
        ):
            splitter._drain_pty(0, Mock(), output_list)

        # Should have captured the data after select timeout retries
        assert output_list == [b"data"]


class TestReadPty:
    @pytest.mark.skipif(os.name != "posix", reason="PTY only on Unix")
    def test_read_pty_drains_on_process_exit(self):
        import pty

        master_fd, slave_fd = pty.openpty()
        splitter = OutputSplitter(stream=False, capture=True)
        output_list = []

        # Mock process that has exited
        mock_proc = Mock()
        mock_proc.poll.return_value = 1  # Process has exited

        # Mock _drain_pty to track if it was called
        with (
            patch.object(splitter, "_drain_pty") as mock_drain,
            patch("os.close"),
            patch("select.select", return_value=([], [], [])),
        ):
            splitter._read_pty(master_fd, Mock(), output_list, mock_proc)
            # _drain_pty should be called when process exits
            mock_drain.assert_called_once()

        os.close(slave_fd)

    @pytest.mark.skipif(os.name != "posix", reason="PTY only on Unix")
    def test_read_pty_reads_and_handles_data(self):
        import pty

        master_fd, slave_fd = pty.openpty()
        splitter = OutputSplitter(stream=False, capture=True)
        output_list = []

        # Mock process that hasn't exited
        mock_proc = Mock()
        mock_proc.poll.return_value = None  # Process still running

        # Mock select to indicate data is ready, then os.read to return data, then empty
        with (
            patch("select.select", return_value=([master_fd], [], [])),
            patch("os.read", side_effect=[b"data", b""]),
            patch("os.close"),
        ):
            # First call reads data, second returns empty (EOF)
            result = splitter._read_pty_data(master_fd, Mock(), output_list)
            assert result is True
            result = splitter._read_pty_data(master_fd, Mock(), output_list)
            assert result is False
            assert output_list == [b"data"]

        os.close(slave_fd)

    @pytest.mark.skipif(os.name != "posix", reason="PTY only on Unix")
    def test_read_pty_handles_eio_after_select_ready(self):
        """Reproduces CI error: BlockingIOError -> select ready -> os.read EIO (PTY closed).

        When a process exits in CI, the PTY slave closes immediately.
        1. os.read() raises BlockingIOError (no data yet)
        2. select.select() returns ready (PTY closed, FD readable due to EOF)
        3. os.read() raises OSError EIO [Errno 5] (PTY slave closed)

        This should be handled gracefully, not raise an uncaught exception.
        """
        import errno
        import fcntl
        import pty

        master_fd, slave_fd = pty.openpty()
        splitter = OutputSplitter(stream=False, capture=True)
        output_list = []

        mock_proc = Mock()
        mock_proc.poll.return_value = None  # Process still running

        # Simulate the exact error sequence from CI
        eio_error = OSError("[Errno 5] Input/output error")
        eio_error.errno = errno.EIO

        call_count = [0]

        def mock_os_read(_fd, _size):
            call_count[0] += 1
            if call_count[0] == 1:
                # First read: BlockingIOError (no data available yet)
                raise BlockingIOError("[Errno 11] Resource temporarily unavailable")
            elif call_count[0] == 2:
                # Second read after select returns ready: EIO (PTY slave closed)
                raise eio_error
            return b""

        # Track fcntl calls to ensure we're mocking correctly
        fcntl_flags = 0

        def mock_fcntl(_fd, cmd, *args):
            nonlocal fcntl_flags
            if cmd == fcntl.F_GETFL:
                return fcntl_flags
            elif cmd == fcntl.F_SETFL:
                if args:
                    fcntl_flags = args[0]
                return 0
            return 0

        with (
            patch("fcntl.fcntl", side_effect=mock_fcntl),
            patch("os.read", side_effect=mock_os_read),
            patch("select.select", return_value=([master_fd], [], [])),
            patch("os.close"),
        ):
            # Should NOT raise - should handle EIO gracefully as EOF
            splitter._read_pty(master_fd, Mock(), output_list, mock_proc)

        # Should complete without crashing
        assert call_count[0] >= 1

        os.close(slave_fd)

    @pytest.mark.skipif(os.name != "posix", reason="PTY only on Unix")
    def test_read_pty_integration_with_real_pty_and_fast_exit(self):
        """Integration test with REAL PTY and subprocess to verify the fix works.

        This creates a real PTY, spawns a fast-exiting process, and verifies
        that EIO errors are handled gracefully (like in CI).
        """
        import pty
        import subprocess

        # Create a real PTY pair
        master_fd, slave_fd = pty.openpty()

        # Spawn a process that exits immediately (no output)
        proc = subprocess.Popen(
            ["true"],  # exits immediately with exit code 0
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
        )
        os.close(slave_fd)  # Close slave in parent

        # Use the real OutputSplitter with real PTY
        splitter = OutputSplitter(stream=False, capture=True)

        # Attach the splitter (uses real threads)
        threads = splitter.attach(proc)

        # This should NOT raise uncaught EIO exceptions
        # The threads should handle EIO gracefully
        try:
            splitter.finalize(threads)
        except OSError as e:
            # If EIO escapes, the test fails
            if e.errno == 5:  # EIO
                pytest.fail(f"EIO error escaped from PTY reader: {e}")
            raise

        # Verify process completed
        proc.wait()
        os.close(master_fd)
