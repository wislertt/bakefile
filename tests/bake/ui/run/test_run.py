import logging
import sys
from pathlib import Path

import pytest
import typer
from loguru import logger

from bake.ui import run
from bake.ui.logger import (
    capsys_to_logs,
    capsys_to_logs_pretty,
    capture_to_logs,
    capture_to_logs_pretty,
    setup_logging,
)
from tests.utils.flaky import flaky_on_macos_ci


def test_run_simple_command(capsys: pytest.CaptureFixture[str]) -> None:
    setup_logging(level_per_module={"": logging.DEBUG}, is_pretty_log=False)
    _ = capsys.readouterr()

    result = run(["echo", "hello"])

    assert result.returncode == 0
    assert result.stdout == "hello\n"
    assert result.stderr == ""

    logs = capsys_to_logs(capsys)
    assert any("[run] echo hello" in log["message"] for log in logs)
    assert any("[done] echo hello" in log["message"] for log in logs)


def test_run_with_elapsed_time_in_logs(capsys: pytest.CaptureFixture[str]) -> None:
    setup_logging(level_per_module={"": logging.DEBUG}, is_pretty_log=False)
    _ = capsys.readouterr()

    run(["echo", "test"])

    logs = capsys_to_logs(capsys)
    done_log = next(log for log in logs if "[done]" in log["message"])
    assert "elapsed_seconds" in done_log
    assert done_log["elapsed_seconds"] >= 0


def test_run_capture_false_returns_none_stdout_stderr() -> None:
    result = run(["echo", "hello"], capture_output=False)

    assert result.returncode == 0
    assert result.stdout is None
    assert result.stderr is None


def test_run_with_cwd(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    setup_logging(level_per_module={"": logging.DEBUG}, is_pretty_log=False)
    _ = capsys.readouterr()

    (tmp_path / "test.txt").write_text("content")

    result = run(["cat", "test.txt"], cwd=tmp_path)

    assert result.stdout == "content"

    logs = capsys_to_logs(capsys)
    assert any("cwd" in log for log in logs)


def test_run_check_false_no_exception_on_error() -> None:
    result = run(["false"], check=False)

    assert result.returncode == 1


def test_run_check_true_raises_on_error() -> None:
    with pytest.raises(typer.Exit):
        run(["false"], check=True)


@pytest.mark.parametrize(
    "stream, capture_output",
    [
        (True, True),
        (True, False),
        (False, True),
        # Note: (False, False) is invalid - at least one must be True
    ],
)
def test_run_with_stream_and_capture_combinations(
    stream: bool,
    capture_output: bool,
    capsys: pytest.CaptureFixture[str],
) -> None:
    setup_logging(level_per_module={"": logging.DEBUG}, is_pretty_log=False)
    _ = capsys.readouterr()

    result = run(["echo", "streamed"], stream=stream, capture_output=capture_output)

    assert result.returncode == 0

    if capture_output:
        assert result.stdout is not None
        assert "streamed" in result.stdout.strip()
    else:
        assert result.stdout is None

    capture = capsys.readouterr()

    if stream:
        assert "streamed" in capture.out.strip()
    else:
        assert capture.out.strip() == ""

    logs = capture_to_logs(capture)
    assert any("[run] echo streamed" in log["message"] for log in logs)


def test_run_stream_and_capture_both_false_raises_error() -> None:
    with pytest.raises(
        ValueError, match="At least one of `stream` or `capture_output` must be True"
    ):
        run(["echo", "test"], stream=False, capture_output=False)


def test_run_returncode_in_logs(capsys: pytest.CaptureFixture[str]) -> None:
    setup_logging(level_per_module={"": logging.DEBUG}, is_pretty_log=False)
    _ = capsys.readouterr()

    run(["true"])

    logs = capsys_to_logs(capsys)
    done_log = next(log for log in logs if "[done]" in log["message"])
    assert "returncode" in done_log
    assert done_log["returncode"] == 0


@flaky_on_macos_ci()
def test_run_stdout_stderr_in_logs(capsys: pytest.CaptureFixture[str]) -> None:
    setup_logging(level_per_module={"": logging.DEBUG}, is_pretty_log=False)
    _ = capsys.readouterr()

    run(["echo", "output"])

    logs = capsys_to_logs(capsys)
    done_log = next(log for log in logs if "[done]" in log["message"])
    assert "stdout" in done_log
    assert "output" in done_log["stdout"]


def test_run_stream_with_capture_false_returns_none_stdout_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    setup_logging(level_per_module={"": logging.DEBUG}, is_pretty_log=False)
    _ = capsys.readouterr()

    result = run(["echo", "test"], stream=True, capture_output=False)

    assert result.returncode == 0
    assert result.stdout is None
    assert result.stderr is None


def test_capture_to_logs_pretty_with_no_output_returns_empty_list(
    capsys: pytest.CaptureFixture[str],
) -> None:
    setup_logging(level_per_module={"": logging.DEBUG}, is_pretty_log=True)
    _ = capsys.readouterr()

    logs = capsys_to_logs_pretty(capsys)

    assert logs == []


def test_capture_to_logs_pretty_direct_with_capture_result() -> None:
    """Test capture_to_logs_pretty directly with a CaptureResult object."""
    from _pytest.capture import CaptureResult

    capture = CaptureResult(out="", err="")
    logs = capture_to_logs_pretty(capture)

    assert logs == []


def test_capture_to_logs_pretty_with_logs_parses_correctly(
    capsys: pytest.CaptureFixture[str],
) -> None:
    setup_logging(level_per_module={"": logging.DEBUG}, is_pretty_log=True)
    _ = capsys.readouterr()

    logger.info("test message")
    logger.debug("debug message")

    logs = capsys_to_logs_pretty(capsys)

    assert len(logs) >= 2
    assert any(log["level"] == "INFO" and "test message" in log["message"] for log in logs)
    assert any(log["level"] == "DEBUG" and "debug message" in log["message"] for log in logs)


def test_capture_to_logs_pretty_with_extra_parses_correctly(
    capsys: pytest.CaptureFixture[str],
) -> None:
    setup_logging(level_per_module={"": logging.DEBUG}, is_pretty_log=True)
    _ = capsys.readouterr()

    test_path = Path("/tmp/test/bakefile.py")
    logger.info("test with extra", extra={"bakefile_path": test_path, "count": 42})

    logs = capsys_to_logs_pretty(capsys)

    assert len(logs) == 1
    log = logs[0]
    assert log["level"] == "INFO"
    assert log["message"] == "test with extra"
    assert Path(log["bakefile_path"]) == Path("/tmp/test/bakefile.py")
    assert log["count"] == 42


def test_run_stream_preserves_colors_with_pty(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Cross-platform version of ANSI color preservation test using Python."""
    # Use Python to generate colored output (works on all platforms)
    python_code = """print('\\033[32mGreen text\\033[0m')
print('\\033[1;34mBlue bold text\\033[0m')
print('\\033[33mYellow text\\033[0m')"""
    script = [sys.executable, "-c", python_code]

    # With stream=True, PTY should preserve ANSI codes
    result = run(script, stream=True, capture_output=True)

    # Should contain ANSI color codes
    assert "[32m" in result.stdout
    assert "[1;34m" in result.stdout
    assert "[33m" in result.stdout
    assert "Green text" in result.stdout
    assert "Blue bold text" in result.stdout
    assert "Yellow text" in result.stdout

    capture = capsys.readouterr()
    assert "[32m" in capture.out
    assert "[1;34m" in capture.out
    assert "[33m" in capture.out
    assert "Green text" in capture.out
    assert "Blue bold text" in capture.out
    assert "Yellow text" in capture.out


# ============================================================================
# String Command Tests (Shell Support)
# ============================================================================


@pytest.mark.parametrize(
    "cmd,expected_in_output",
    [
        ("echo hello from shell", "hello from shell"),
        ("echo hello && echo world", ["hello", "world"]),
        ("echo hello | tr h H", "Hello"),
    ],
)
def test_run_string_command_shell_features(
    cmd: str,
    expected_in_output: str | list[str],
) -> None:
    result = run(cmd)

    assert result.returncode == 0
    if isinstance(expected_in_output, str):
        assert expected_in_output in result.stdout
    else:
        for expected in expected_in_output:
            assert expected in result.stdout


@pytest.mark.parametrize(
    "cmd_type,cmd,shell_override",
    [
        # String commands with different shell overrides
        ("str", "echo test", None),  # Auto-detect: shell=True
        ("str", "echo test && echo success", None),  # Auto-detect with chaining
        ("str", "echo test", True),  # Explicit shell=True
        # List commands (backward compatibility)
        ("list", ["echo", "test"], None),  # Auto-detect: shell=False
        ("list", ["echo", "test"], False),  # Explicit shell=False
    ],
)
def test_run_command_auto_detection(
    cmd_type: str,
    cmd: str | list[str],
    shell_override: bool | None,
) -> None:
    result = run(cmd, shell=shell_override)

    assert result.returncode == 0
    if cmd_type == "str" and "&&" in str(cmd):
        assert "test" in result.stdout
        assert "success" in result.stdout
    else:
        assert "test" in result.stdout


def test_run_string_command_wildcards(tmp_path: Path) -> None:
    """Test wildcards expand in string commands."""
    (tmp_path / "test1.py").write_text("# test1")
    (tmp_path / "test2.py").write_text("# test2")
    (tmp_path / "README.md").write_text("# readme")

    result = run("ls *.py", cwd=tmp_path)

    assert result.returncode == 0
    assert "test1.py" in result.stdout
    assert "test2.py" in result.stdout
    assert "README.md" not in result.stdout


def test_run_string_command_redirects(tmp_path: Path) -> None:
    result = run("echo test content > test.txt", cwd=tmp_path)

    assert result.returncode == 0
    content = (tmp_path / "test.txt").read_text()
    assert content.strip() == "test content"


def test_run_string_command_preserves_colors_with_pty() -> None:
    result = run('printf "\\033[32mGreen\\033[0m\\n"', shell=True)

    assert result.returncode == 0
    assert "[32m" in result.stdout
    assert "Green" in result.stdout


@pytest.mark.parametrize(
    "cmd,capture_output",
    [
        ("echo test", False),
        (["echo", "test"], False),
    ],
)
def test_run_command_capture_output_false(
    capsys: pytest.CaptureFixture[str],
    cmd: str | list[str],
    capture_output: bool,
) -> None:
    setup_logging(level_per_module={"": logging.DEBUG}, is_pretty_log=False)
    _ = capsys.readouterr()

    result = run(cmd, capture_output=capture_output)

    assert result.returncode == 0
    assert result.stdout is None
    assert result.stderr is None


def test_run_string_command_with_explicit_shell_false() -> None:
    # When shell=False, a string command is treated as a single executable name
    # On Unix: "echo hello" is not a valid executable -> raises FileNotFoundError
    # On Windows: Windows CreateProcess may handle this differently
    if sys.platform == "win32":
        # On Windows, CreateProcess tokenizes the command, so "echo hello" finds echo.exe/bat
        # and "hello" is passed as an argument. Output is captured in stdout.
        result = run("echo hello", shell=False)
        assert result.returncode == 0
        assert "hello" in result.stdout
    else:
        # On Unix, this should raise FileNotFoundError
        result = run("echo hello", shell=True)
        with pytest.raises(FileNotFoundError):
            run("echo hello", shell=False)
