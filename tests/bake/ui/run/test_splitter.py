import subprocess
from unittest.mock import Mock, patch

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
