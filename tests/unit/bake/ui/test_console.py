from unittest import mock

import pytest

from bake.ui import console


class TestSuccess:
    def test_success_prints_to_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
        console.success("Operation completed")
        captured = capsys.readouterr()
        assert "SUCCESS" in captured.out
        assert "Operation completed" in captured.out
        assert captured.err == ""


class TestEcho:
    def test_echo_prints_to_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
        console.echo("Processing data")
        captured = capsys.readouterr()
        assert "Processing data" in captured.out
        assert captured.err == ""

    def test_echo_with_various_types(self, capsys: pytest.CaptureFixture[str]) -> None:
        console.echo(42)
        console.echo(["item1", "item2"])
        captured = capsys.readouterr()
        assert "42" in captured.out
        assert "item1" in captured.out


class TestWarning:
    def test_warning_prints_to_stderr(self, capsys: pytest.CaptureFixture[str]) -> None:
        console.warning("File not found")
        captured = capsys.readouterr()
        assert "WARNING" in captured.err
        assert "File not found" in captured.err
        assert captured.out == ""


class TestError:
    def test_error_prints_to_stderr(self, capsys: pytest.CaptureFixture[str]) -> None:
        console.error("Failed to connect")
        captured = capsys.readouterr()
        assert "ERROR" in captured.err
        assert "Failed to connect" in captured.err
        assert captured.out == ""


class TestOutputToCorrectStream:
    @pytest.mark.parametrize(
        "func_name,stream_name",
        [
            ("success", "out"),
            ("echo", "out"),
            ("warning", "err"),
            ("error", "err"),
            ("script_block", "err"),
        ],
    )
    def test_outputs_to_correct_stream(
        self,
        capsys: pytest.CaptureFixture[str],
        func_name: str,
        stream_name: str,
    ) -> None:
        if func_name == "script_block":
            getattr(console, func_name)("Test Title", "echo 'test'")
        else:
            getattr(console, func_name)("Test message")
        captured = capsys.readouterr()
        output = getattr(captured, stream_name)
        assert "Test" in output
        other_stream = "err" if stream_name == "out" else "out"
        assert getattr(captured, other_stream) == ""


class TestScriptBlock:
    def test_script_block_prints_to_stderr(self, capsys: pytest.CaptureFixture[str]) -> None:
        console.script_block(
            "Bootstrap Project",
            """#!/usr/bin/env bash
            set -euo pipefail

            log() {
                printf "[%(%Y-%m-%d %H:%M:%S)T] %s\\\\n" -1 "$*"
            }

            log "Creating virtual environment..."
            python -m venv .venv

            source .venv/bin/activate

            log "Installing dependencies..."
            pip install -r requirements.txt

            log "Running migrations..."
            alembic upgrade head

            log "Bootstrap complete ✅"
            """,
        )
        captured = capsys.readouterr()
        assert "Bootstrap Project" in captured.err
        assert '\nlog "Bootstrap complete' in captured.err
        assert captured.out == ""

    def test_script_block_has_bold_lines(self, capsys: pytest.CaptureFixture[str]) -> None:
        console.script_block("Test", "echo 'hello'")
        captured = capsys.readouterr()
        assert "━" in captured.err  # bold line character
        assert "─" in captured.err  # thin line character


def test_warning_prints_github_actions_format(capsys: pytest.CaptureFixture[str]) -> None:
    with mock.patch("bake.ui.console.bake_settings") as mock_settings:
        mock_settings.github_actions = True
        console.warning("File not found")
        captured = capsys.readouterr()
        assert "::warning::File not found" in captured.err
        assert captured.out == ""


def test_error_prints_github_actions_format(capsys: pytest.CaptureFixture[str]) -> None:
    with mock.patch("bake.ui.console.bake_settings") as mock_settings:
        mock_settings.github_actions = True
        console.error("Failed to connect")
        captured = capsys.readouterr()
        assert "::error::Failed to connect" in captured.err
        assert captured.out == ""


def test_cmd_prints_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    console.cmd("pytest tests/")
    captured = capsys.readouterr()
    assert "pytest tests/" in captured.err
    assert "❯" in captured.err  # noqa: RUF001
    assert captured.out == ""


def test_script_block_falls_back_to_dedent_on_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with mock.patch("bake.ui.console.BashFormatter") as mock_formatter:
        mock_formatter.return_value.beautify_string.return_value = ("", "error message")
        console.script_block("Test", "    echo 'indented'")
        captured = capsys.readouterr()
        assert "Test" in captured.err
        assert "echo 'indented'" in captured.err
        assert captured.out == ""


def test_prefix_out_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    console.prefix_out("Task complete", emoji=":check:", label="DONE", style="bold green")
    captured = capsys.readouterr()
    assert "DONE" in captured.out
    assert "Task complete" in captured.out
    assert captured.err == ""


def test_prefix_out_without_emoji(capsys: pytest.CaptureFixture[str]) -> None:
    console.prefix_out("Just info", label="INFO", style="bold blue")
    captured = capsys.readouterr()
    assert "INFO" in captured.out
    assert "Just info" in captured.out


def test_prefix_err_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    console.prefix_err("Task failed", emoji=":x:", label="FAIL", style="bold red")
    captured = capsys.readouterr()
    assert "FAIL" in captured.err
    assert "Task failed" in captured.err
    assert captured.out == ""


def test_prefix_err_without_emoji(capsys: pytest.CaptureFixture[str]) -> None:
    console.prefix_err("Warning message", label="WARN", style="bold yellow")
    captured = capsys.readouterr()
    assert "WARN" in captured.err
    assert "Warning message" in captured.err
