import inspect
import logging
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

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
from bake.ui.run import run as run_fn
from bake.ui.run import run_script, run_uv
from tests.utils.misc import flaky_on_macos_ci


@flaky_on_macos_ci()
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


@flaky_on_macos_ci()
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


@flaky_on_macos_ci()
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


@pytest.mark.parametrize(
    "stream, capture_output",
    [
        (True, True),
        (True, False),
        (False, True),
        # Note: (False, False) is invalid - at least one must be True
    ],
)
def test_run_stderr_is_captured_and_streamed(
    capsys: pytest.CaptureFixture[str],
    stream: bool,
    capture_output: bool,
) -> None:
    # Clear any previous output from capsys
    capsys.readouterr()

    result = run(
        'echo "error message" >&2',
        stream=stream,
        capture_output=capture_output,
        echo=False,
        check=False,
    )

    assert result.returncode == 0
    if capture_output:
        assert isinstance(result.stderr, str)
        assert "error message" in result.stderr, "stderr should be captured"
    else:
        assert result.stderr is None

    capture = capsys.readouterr()
    if stream:
        assert "error message" in capture.err
    else:
        assert capture.err == ""


# ============================================================================
# String Command Tests (Shell Support)
# ============================================================================


@flaky_on_macos_ci()
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


@flaky_on_macos_ci()
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


# Tests for internal helper functions
class TestParseShebang:
    """Tests for _parse_shebang internal function."""

    @pytest.mark.parametrize(
        "script,expected,is_partial_match",
        [
            # Direct path cases (covers line 42 in run.py)
            ("#!/usr/bin/python3\nprint('hello')", "/usr/bin/python3", False),
            ("#!  /usr/bin/python3  \nprint('hello')", "/usr/bin/python3", False),
            # /usr/bin/env case (covers line 38-39 in run.py) - just check not None
            ("#!/usr/bin/env python3\nprint('hello')", None, True),
            # No shebang cases (covers line 31-32 in run.py)
            ("print('hello')", None, False),
            ("", None, False),
            ("   \n  \n", None, False),
        ],
    )
    def test_parse_shebang(self, script: str, expected: str | None, is_partial_match: bool) -> None:
        """Test parsing various shebang formats."""
        from bake.ui.run.run import _parse_shebang

        result = _parse_shebang(script)

        if is_partial_match:
            # For env wrapper case, just check it found something
            assert result is not None
        else:
            assert result == expected


class TestResolveInterpreter:
    """Tests for _resolve_interpreter internal function."""

    @pytest.mark.parametrize(
        "interpreter,check_func",
        [
            # Absolute path that exists (covers line 49 in run.py)
            pytest.param(
                "/bin/sh" if sys.platform != "win32" else "C:\\Windows\\System32\\cmd.exe",
                lambda x: x is not None,
                marks=pytest.mark.skipif(
                    sys.platform == "win32",
                    reason="Unix-specific path",
                )
                if sys.platform == "win32"
                else [],
                id="absolute_path_exists",
            ),
            # Absolute path that doesn't exist (covers line 49 -> None)
            pytest.param(
                "/nonexistent/path/to/python",
                lambda x: x is None,
                id="absolute_path_not_exists",
            ),
            # Relative path - searches PATH (covers line 52 in run.py)
            pytest.param(
                "python3",
                lambda x: x is None or os.path.isabs(x),  # Either not found or absolute
                id="relative_path_in_path",
            ),
            # Not in PATH (covers line 52 -> None)
            pytest.param(
                "nonexistent_python_xyz",
                lambda x: x is None,
                id="not_in_path",
            ),
        ],
    )
    def test_resolve_interpreter(self, interpreter: str, check_func) -> None:
        """Test resolving interpreter paths."""
        from bake.ui.run.run import _resolve_interpreter

        result = _resolve_interpreter(interpreter)
        assert check_func(result)


# ============================================================================
# echo_cmd Tests (Command Display Override)
# ============================================================================


@flaky_on_macos_ci()
def test_echo_cmd_overrides_all_display_and_logs(capsys: pytest.CaptureFixture[str]) -> None:
    """Test that echo_cmd overrides console echo, [run], [done], and [error] logs."""
    setup_logging(level_per_module={"": logging.DEBUG}, is_pretty_log=False)
    _ = capsys.readouterr()

    result = run(["echo", "hello"], echo_cmd="custom command")

    assert result.returncode == 0
    assert result.stdout == "hello\n"

    capture = capsys.readouterr()
    logs = capture_to_logs(capture)

    # Console echo and debug logs use echo_cmd
    assert "custom command" in capture.err
    assert any("[run] custom command" in log["message"] for log in logs)
    assert any("[done] custom command" in log["message"] for log in logs)

    # Error log also uses echo_cmd
    with pytest.raises(typer.Exit):
        run(["false"], echo_cmd="failing command", check=True)

    capture = capsys.readouterr()
    logs = capture_to_logs(capture)
    assert any("[error] failing command" in log["message"] for log in logs)


@flaky_on_macos_ci()
def test_echo_cmd_executes_actual_command_not_display_string(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that the actual command is executed, not the echo_cmd string."""
    setup_logging(level_per_module={"": logging.DEBUG}, is_pretty_log=False)
    _ = capsys.readouterr()

    result = run(["echo", "test123"], echo_cmd="not a real command")

    assert result.returncode == 0
    assert result.stdout == "test123\n"

    logs = capsys_to_logs(capsys)
    assert any("[run] not a real command" in log["message"] for log in logs)


@flaky_on_macos_ci()
@pytest.mark.parametrize(
    "kwargs,expected_log_prefix,expected_stdout,check_console_echo",
    [
        # echo=False: logs use echo_cmd, console echo is suppressed
        ({"echo": False, "echo_cmd": "custom"}, "custom", "hello\n", False),
        # dry_run=True: [dry-run] log uses echo_cmd, no execution
        ({"dry_run": True, "echo_cmd": "custom"}, "[dry-run] custom", "", False),
        # echo_cmd=None: shows actual command in logs and console
        ({"echo_cmd": None}, "echo hello", "hello\n", True),
    ],
)
def test_echo_cmd_edge_cases(
    capsys: pytest.CaptureFixture[str],
    kwargs: dict,
    expected_log_prefix: str,
    expected_stdout: str,
    check_console_echo: bool,
) -> None:
    """Test echo_cmd with echo=False, dry_run=True, and echo_cmd=None."""
    setup_logging(level_per_module={"": logging.DEBUG}, is_pretty_log=False)
    _ = capsys.readouterr()

    result = run(["echo", "hello"], **kwargs)

    assert result.returncode == 0
    assert result.stdout == expected_stdout

    capture = capsys.readouterr()
    logs = capture_to_logs(capture)

    assert any(expected_log_prefix in log["message"] for log in logs)
    if check_console_echo:
        assert "echo hello" in capture.err


# ============================================================================
# Windows CI Tests
# ============================================================================


class TestCrossPlatformSubprocess:
    """Tests for cross-platform subprocess execution.

    These tests verify that commands with inline environment variables and
    quoted glob patterns work correctly across all platforms (Unix and Windows).

    On Windows CI, these tests reproduce issues with:
    - Inline env vars: `'RUST_BACKTRACE' is not recognized as a command`
    - Quoted patterns: double quotes appear around `'**/tests/**'`
    """

    def test_inline_env_var_with_shell(self) -> None:
        """Test inline environment variables work with shell=True.

        Uses Unix-style syntax `VAR=value command` which should work on all
        platforms when shell=True. On Windows CI, this reproduces the
        `'VAR' is not recognized as a command` error.
        """
        # Test inline env var using Python's os.environ
        cmd = (
            "TEST_VAR=hello_world python -c "
            "\"import os; print(os.environ.get('TEST_VAR', 'NOT_SET'))\""
        )
        result = run(cmd, shell=True, check=False, echo=False)

        # Should succeed and print the variable value
        assert result.returncode == 0, (
            f"Inline env var command failed. stdout: {result.stdout}, stderr: {result.stderr}"
        )
        assert "hello_world" in result.stdout, (
            f"Expected 'hello_world' in stdout, got: {result.stdout}"
        )

    def test_quoted_glob_pattern_arg(self) -> None:
        """Test quoted glob patterns are passed correctly.

        Verifies that quoted args like `'pattern'` are passed to subprocess
        without extra quotes. On Windows CI, this reproduces the double
        quote issue where `'**/tests/**'` becomes `''**/tests/**''`.
        """
        # Test that quoted args are passed correctly using Python's sys.argv
        cmd = "python -c \"import sys; print(sys.argv[1])\" '**/tests/**'"
        result = run(cmd, shell=True, check=False, echo=False)

        # Should succeed and print the pattern without extra quotes
        assert result.returncode == 0, (
            f"Quoted glob pattern command failed. stdout: {result.stdout}, stderr: {result.stderr}"
        )

        # The pattern should be printed without double quotes wrapping it
        # Correct: **/tests/**  Wrong: '**/tests/**' or ''**/tests/**''
        stdout_clean = result.stdout.strip()
        assert stdout_clean == "**/tests/**", (
            f"Expected '**/tests/**' in stdout, got: {stdout_clean!r}"
        )
        # Should NOT have extra quotes wrapping it
        assert not stdout_clean.startswith("'"), f"Pattern has leading quote: {stdout_clean!r}"
        assert not stdout_clean.endswith("'"), f"Pattern has trailing quote: {stdout_clean!r}"

    def test_sh_exe_not_found_error(self) -> None:
        """Test that RuntimeError is raised when sh.exe is not found on Windows."""
        # Mock Windows platform and sh.exe not found
        with (
            mock.patch("sys.platform", "win32"),
            mock.patch("shutil.which", return_value=None),
            pytest.raises(RuntimeError, match=r"sh\.exe not found"),
        ):
            run("echo test", shell=True, echo=False)

    def test_sh_exe_not_found_multiline_script(self) -> None:
        """Test that RuntimeError is raised for multi-line scripts when sh.exe not found."""
        # Mock Windows platform and sh.exe not found
        with (
            mock.patch("sys.platform", "win32"),
            mock.patch("shutil.which", return_value=None),
            pytest.raises(RuntimeError, match=r"sh\.exe not found"),
        ):
            run("echo line1\necho line2", shell=True, echo=False)


# ============================================================================
# _check_exit_code Tests (stream=False error output)
# ============================================================================


class TestCheckExitCodeStreamFalse:
    """Tests for _check_exit_code showing output when stream=False.

    When stream=False and check=True, the output should be shown before
    exiting if the command fails, since the user didn't see it in real-time.
    """

    def test_stream_false_shows_stderr_on_failure(self, capsys: pytest.CaptureFixture[str]) -> None:
        """When stream=False and command fails with stderr, show stderr before exit."""
        _ = capsys.readouterr()

        with pytest.raises(typer.Exit) as exc_info:
            run(["ls", "/nonexistent_path_xyz"], check=True, stream=False, echo=False)

        assert exc_info.value.exit_code != 0
        capture = capsys.readouterr()
        # stderr should be shown since stream=False
        assert "nonexistent_path_xyz" in capture.err

    def test_stream_false_shows_stdout_when_no_stderr(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """When stream=False, no stderr, but has stdout, show stdout before exit."""
        _ = capsys.readouterr()

        # Create a command that fails with stdout but no stderr
        cmd = [sys.executable, "-c", "import sys; print('output on stdout'); sys.exit(1)"]

        with pytest.raises(typer.Exit) as exc_info:
            run(cmd, check=True, stream=False, echo=False)

        assert exc_info.value.exit_code == 1
        capture = capsys.readouterr()
        # stdout should be shown since stream=False and no stderr
        assert "output on stdout" in capture.err

    def test_stream_false_shows_generic_error_when_no_output(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """When stream=False, no stderr/stdout, show generic error message before exit."""
        _ = capsys.readouterr()

        # Create a command that fails silently (no output)
        cmd = [sys.executable, "-c", "import sys; sys.exit(42)"]

        with pytest.raises(typer.Exit) as exc_info:
            run(cmd, check=True, stream=False, echo=False)

        assert exc_info.value.exit_code == 42
        capture = capsys.readouterr()
        # Generic error message should be shown
        assert "Command" in capture.err
        # Check with whitespace flexibility (console may wrap)
        assert "failed" in capture.err
        # Strip ANSI codes for checking the exit code message
        import re

        err_plain = re.sub(r"\x1b\[[0-9;]*m", "", capture.err)
        assert "exit code 42" in err_plain

    def test_stream_false_truncates_long_command_in_error(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """When stream=False and no output, long commands are truncated in error message."""
        _ = capsys.readouterr()

        # Create a very long command that fails silently (no stdout/stderr)
        long_arg = "x" * 100
        # Use actual newline so the comment doesn't swallow sys.exit
        cmd = [sys.executable, "-c", f"# {long_arg}\nimport sys\nsys.exit(1)"]

        with pytest.raises(typer.Exit):
            run(cmd, check=True, stream=False, echo=False)

        capture = capsys.readouterr()
        # The error message should contain truncated command with "..."
        assert "..." in capture.err

    def test_stream_false_short_command_not_truncated(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """When stream=False and no output, short commands are NOT truncated."""
        _ = capsys.readouterr()

        # Create a short command that fails silently
        # Use echo_cmd to ensure command is short enough (< 50 chars)
        with pytest.raises(typer.Exit):
            run(["false"], check=True, stream=False, echo=False, echo_cmd="short")

        capture = capsys.readouterr()
        # The error message should NOT contain "..." for short commands
        assert "..." not in capture.err
        # The short command should be shown in full
        import re

        err_plain = re.sub(r"\x1b\[[0-9;]*m", "", capture.err)
        assert "short" in err_plain

    @flaky_on_macos_ci()
    def test_stream_true_does_not_show_duplicate_stderr(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """When stream=True, stderr is shown during streaming, not again before exit."""
        _ = capsys.readouterr()

        with pytest.raises(typer.Exit):
            run(["ls", "/nonexistent_path_xyz"], check=True, stream=True, echo=False)

        capture = capsys.readouterr()
        # stderr appears once (from streaming), not duplicated
        assert "nonexistent_path_xyz" in capture.err
        # Should not have the generic error message
        assert "failed with exit code" not in capture.err


# ============================================================================
# Timeout Tests
# ============================================================================


class TestTimeout:
    """Tests for the timeout parameter."""

    @pytest.mark.parametrize("stream", [True, False])
    def test_timeout_raises_timeout_expired(self, stream: bool) -> None:
        """TimeoutExpired is raised when command exceeds timeout."""
        # sleep 10 should exceed 0.1 second timeout
        with pytest.raises(subprocess.TimeoutExpired):
            run("sleep 10", timeout=0.1, stream=stream, echo=False)

    @flaky_on_macos_ci()
    @pytest.mark.parametrize("stream", [True, False])
    def test_timeout_completes_within_limit(self, stream: bool) -> None:
        """Command completes successfully when within timeout."""
        result = run(["echo", "fast"], timeout=5.0, stream=stream, echo=False)

        assert result.returncode == 0
        assert "fast" in result.stdout

    @flaky_on_macos_ci()
    @pytest.mark.parametrize("stream", [True, False])
    def test_timeout_none_waits_indefinitely(self, stream: bool) -> None:
        """timeout=None (default) waits for command to complete."""
        # This should complete, not raise timeout
        result = run(["echo", "no timeout"], timeout=None, stream=stream, echo=False)

        assert result.returncode == 0
        assert "no timeout" in result.stdout

    def test_timeout_stream_shows_output_before_timeout(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """When streaming with timeout, output is shown before timeout occurs."""
        _ = capsys.readouterr()

        # Command that outputs before sleeping
        cmd = 'echo "before timeout" && sleep 10'

        with pytest.raises(subprocess.TimeoutExpired):
            run(cmd, timeout=0.5, stream=True, echo=False)

        capture = capsys.readouterr()
        # Output should have been streamed before timeout
        assert "before timeout" in capture.out

    def test_timeout_kills_process(self) -> None:
        """Timed out process is killed (not left running)."""
        import time

        # Use a long-running command
        start = time.perf_counter()

        with pytest.raises(subprocess.TimeoutExpired):
            run("sleep 60", timeout=0.2, stream=True, echo=False)

        elapsed = time.perf_counter() - start

        # If process wasn't killed, this would take ~60 seconds
        # With kill, it should be near the timeout value
        assert elapsed < 2.0, f"Process may not have been killed, elapsed={elapsed}s"


# ============================================================================
# Signature Compatibility Tests
# ============================================================================


class TestSignatureCompatibility:
    """Tests to ensure run wrappers have compatible signatures with run()."""

    def test_run_script_has_common_params(self) -> None:
        """run_script should have all common params from run()."""
        excluded = {
            "cmd",  # uses 'script' instead
            "shell",  # always uses shell=True
            "echo_cmd",  # handles its own display
            "_encoding",  # private param
        }
        run_params = set(inspect.signature(run_fn).parameters.keys())
        script_params = set(inspect.signature(run_script).parameters.keys())
        expected = run_params - excluded

        missing = expected - script_params
        assert not missing, f"run_script missing params: {missing}"

    def test_run_uv_has_common_params(self) -> None:
        """run_uv should have all common params from run()."""
        excluded = {
            "cmd",  # constructs its own from uv_bin + args
            "shell",  # always uses shell=False
            "echo_cmd",  # handles its own display
            "_encoding",  # private param
        }
        run_params = set(inspect.signature(run_fn).parameters.keys())
        uv_params = set(inspect.signature(run_uv).parameters.keys())
        expected = run_params - excluded

        missing = expected - uv_params
        assert not missing, f"run_uv missing params: {missing}"
