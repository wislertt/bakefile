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
