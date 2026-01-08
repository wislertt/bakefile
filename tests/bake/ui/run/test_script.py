import pytest

from bake.ui.run import run_script


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
    script = """
echo hello
echo world
"""
    result = run_script("Multi-line", script)

    assert result.returncode == 0
    assert result.stdout is not None
    assert "hello" in result.stdout
    assert "world" in result.stdout
