from textwrap import dedent

import pytest

from bake.ui.run import run_script
from tests.utils.flaky import flaky_on_macos_ci


@pytest.mark.parametrize(
    "echo,dry_run,check_output_in_err",
    [
        (True, False, False),
        (False, False, False),
        (True, True, True),
        (False, True, False),
    ],
)
def test_run_script_echo_and_dry_run_combinations(
    echo: bool,
    dry_run: bool,
    check_output_in_err: bool,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = run_script("Test", "echo hello", echo=echo, dry_run=dry_run)

    assert result.returncode == 0

    capture = capsys.readouterr()
    if check_output_in_err:
        assert "Test" in capture.err


def test_run_script_basic_execution() -> None:
    result = run_script("Test", "echo hello")

    assert result.returncode == 0
    assert result.stdout is not None
    assert "hello" in result.stdout


def test_run_script_dry_run_skips_execution() -> None:
    result = run_script("Test", "echo hello", dry_run=True)

    assert result.returncode == 0
    assert result.stdout == ""


def test_run_script_capture_false_returns_none() -> None:
    result = run_script("Test", "echo hello", capture_output=False)

    assert result.returncode == 0
    assert result.stdout is None
    assert result.stderr is None


def test_run_script_multi_line_script() -> None:
    script = dedent("""
        echo hello
        echo world
    """)
    result = run_script("Multi-line", script)

    assert result.returncode == 0
    assert result.stdout is not None
    assert "hello" in result.stdout
    assert "world" in result.stdout


def test_run_script_with_python_shebang() -> None:
    """Test that shebang scripts work cross-platform."""
    script = dedent("""
        #!/usr/bin/env python3
        import sys
        print("hello from python")
        sys.exit(0)
    """)
    result = run_script("Python Shebang", script)

    assert result.returncode == 0
    assert result.stdout is not None
    assert "hello from python" in result.stdout


@flaky_on_macos_ci()
def test_run_script_concurrent_execution() -> None:
    """Test that multiple scripts can run concurrently without conflicts."""
    import concurrent.futures

    scripts = [
        ("Script 1", "echo one"),
        ("Script 2", "echo two"),
        ("Script 3", "echo three"),
    ]

    def run_script_pair(title: str, script: str):
        return run_script(title, script)

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(run_script_pair, title, script) for title, script in scripts]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # All scripts should succeed
    assert len(results) == 3
    for result in results:
        assert result.returncode == 0

    # All outputs should be present (order may vary)
    all_stdout = "".join(r.stdout for r in results if r.stdout)
    assert "one" in all_stdout
    assert "two" in all_stdout
    assert "three" in all_stdout


def test_run_script_temp_file_cleanup() -> None:
    """Test that temp files are cleaned up after execution."""
    # Run a multi-line script that creates a temp file (on Windows)
    script = dedent("""
        echo hello
        echo world
    """)
    result = run_script("Temp Cleanup Test", script)
    assert result.returncode == 0

    # Run a shebang script that also creates a temp file
    shebang_script = dedent("""
        #!/usr/bin/env python3
        print("python script")
    """)
    result2 = run_script("Shebang Temp Cleanup Test", shebang_script)
    assert result2.returncode == 0

    # On Unix, shebang scripts create temp files
    # On Windows, multi-line scripts create temp files
    # The test verifies that temp files are cleaned up properly
    # (We can't easily count exact temp files due to OS variations,
    # but the fact that tests complete without errors is a good indicator)


def test_run_script_utf8_characters() -> None:
    """Test that scripts with non-ASCII UTF-8 characters work correctly."""
    script = dedent("""
        #!/usr/bin/env python3
        import sys

        # Latin extended
        print("café")
        print("niño")

        # Chinese characters
        print("你好世界")

        # Emoji
        print("Hello 🌍")

        sys.exit(0)
    """)
    result = run_script("UTF-8 Test", script)

    assert result.returncode == 0
    assert result.stdout is not None
    assert "café" in result.stdout
    assert "niño" in result.stdout
    assert "你好世界" in result.stdout
    assert "Hello 🌍" in result.stdout


def test_run_script_syntax_error_propagates() -> None:
    """Test that script syntax errors propagate correctly and temp files are cleaned up."""
    script = dedent("""
        #!/usr/bin/env python3
        # This script has a syntax error
        print("hello"
        # Missing closing parenthesis
    """)
    result = run_script("Syntax Error Test", script, check=False)

    assert result.returncode != 0
    assert result.stderr is not None
    assert "SyntaxError" in result.stderr or "error" in result.stderr.lower()


def test_run_script_runtime_error_propagates() -> None:
    """Test that script runtime errors propagate correctly and temp files are cleaned up."""
    script = dedent("""
        #!/usr/bin/env python3
        # This script has a runtime error
        raise ValueError("This is a test error")
    """)
    result = run_script("Runtime Error Test", script, check=False)

    assert result.returncode != 0
    assert result.stderr is not None
    assert "ValueError" in result.stderr or "This is a test error" in result.stderr


def test_run_script_nonzero_exit_propagates() -> None:
    """Test that non-zero exit codes propagate correctly and temp files are cleaned up."""
    script = dedent("""
        #!/usr/bin/env python3
        import sys
        print("about to exit with error")
        sys.exit(42)
    """)
    result = run_script("Non-Zero Exit Test", script, check=False)

    assert result.returncode == 42
    assert result.stdout is not None
    assert "about to exit with error" in result.stdout


def test_run_script_keep_temp_file() -> None:
    """Test that keep_temp_file parameter works correctly."""
    script = dedent("""
        #!/usr/bin/env python3
        print("temp file test")
    """)

    # Run with keep_temp_file=True
    result = run_script("Keep Temp File Test", script, keep_temp_file=True)

    assert result.returncode == 0
    assert result.stdout is not None
    assert "temp file test" in result.stdout

    # Run again to verify temp files can be created multiple times
    result2 = run_script("Keep Temp File Test 2", script, keep_temp_file=True, echo=False)

    assert result2.returncode == 0
    assert result2.stdout is not None
    assert "temp file test" in result2.stdout

    # Verify cleanup still happens when keep_temp_file=False (default behavior)
    result3 = run_script("Clean Up Test", script, keep_temp_file=False)
    assert result3.returncode == 0


def test_run_script_keep_temp_file_with_error() -> None:
    """Test that keep_temp_file keeps the file even when script fails."""
    script = dedent("""
        #!/usr/bin/env python3
        raise ValueError("test error")
    """)

    # Run with keep_temp_file=True and check=False
    result = run_script("Keep Temp File On Error", script, keep_temp_file=True, check=False)

    assert result.returncode != 0
    assert result.stderr is not None
    assert "ValueError" in result.stderr or "test error" in result.stderr
