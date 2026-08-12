import inspect
from unittest import mock

import pytest
from rich.console import Console as RichConsole

from bake.ui import console
from bake.ui.logger.capsys import strip_ansi
from tests.utils.cli import get_error_label, get_warning_label


class TestConsoleSignature:
    """Test that our custom Console matches Rich's Console signature."""

    def test_print_signature_matches_rich(self) -> None:
        """Our Console.print should have the same signature as Rich's Console.print."""
        rich_sig = inspect.signature(RichConsole.print)
        our_sig = inspect.signature(console.Console.print)

        rich_params = rich_sig.parameters
        our_params = our_sig.parameters

        # All parameter names should match
        assert set(rich_params.keys()) == set(our_params.keys()), (
            f"Parameter names don't match.\n"
            f"Rich: {set(rich_params.keys())}\n"
            f"Our:  {set(our_params.keys())}"
        )

    def test_print_has_custom_overflow_default(self) -> None:
        """Our Console.print should default overflow='ignore'."""
        our_sig = inspect.signature(console.Console.print)
        overflow_param = our_sig.parameters["overflow"]
        assert overflow_param.default == "ignore", (
            f"Expected overflow default='ignore', got '{overflow_param.default}'"
        )

    def test_print_has_custom_crop_default(self) -> None:
        """Our Console.print should default crop=False."""
        our_sig = inspect.signature(console.Console.print)
        crop_param = our_sig.parameters["crop"]
        assert crop_param.default is False, (
            f"Expected crop default=False, got '{crop_param.default}'"
        )

    def test_other_params_match_rich_defaults(self) -> None:
        """Other parameters should match Rich's defaults (except overflow, crop)."""
        rich_sig = inspect.signature(RichConsole.print)
        our_sig = inspect.signature(console.Console.print)

        for name, rich_param in rich_sig.parameters.items():
            if name in ("overflow", "crop", "self"):
                continue
            our_param = our_sig.parameters[name]
            assert rich_param.default == our_param.default, (
                f"Parameter '{name}' default mismatch.\n"
                f"Rich: {rich_param.default}\n"
                f"Our:  {our_param.default}"
            )


class TestSuccess:
    def test_success_prints_to_stderr(self, capsys: pytest.CaptureFixture[str]) -> None:
        console.success("Operation completed")
        captured = capsys.readouterr()
        assert "SUCCESS" in captured.err
        assert "Operation completed" in captured.err
        assert captured.out == ""


class TestStart:
    def test_start_prints_to_stderr(self, capsys: pytest.CaptureFixture[str]) -> None:
        console.start("Updating dependencies")
        captured = capsys.readouterr()
        assert "START" in captured.err
        assert "Updating dependencies" in strip_ansi(captured.err)
        assert captured.out == ""

    def test_start_adds_ellipsis_suffix(self, capsys: pytest.CaptureFixture[str]) -> None:
        console.start("Running task")
        captured = capsys.readouterr()
        assert "Running task..." in strip_ansi(captured.err)
        assert captured.out == ""


class TestInfo:
    def test_info_prints_to_stderr(self, capsys: pytest.CaptureFixture[str]) -> None:
        console.info("Processing data")
        captured = capsys.readouterr()
        assert "INFO" in captured.err
        assert "Processing data" in captured.err
        assert captured.out == ""

    def test_info_with_custom_label(self, capsys: pytest.CaptureFixture[str]) -> None:
        console.info("Custom message", label="CUSTOM")
        captured = capsys.readouterr()
        assert "CUSTOM" in captured.err
        assert "Custom message" in captured.err
        assert captured.out == ""


class TestEnd:
    def test_end_prints_to_stderr(self, capsys: pytest.CaptureFixture[str]) -> None:
        console.end("Process complete")
        captured = capsys.readouterr()
        assert "END" in captured.err
        assert "Process complete" in captured.err
        assert captured.out == ""

    def test_end_does_not_add_ellipsis(self, capsys: pytest.CaptureFixture[str]) -> None:
        console.end("Done")
        captured = capsys.readouterr()
        assert "Done" in strip_ansi(captured.err)
        assert "Done..." not in strip_ansi(captured.err)
        assert captured.out == ""


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
    @pytest.mark.parametrize("github_actions", [False, True])
    def test_warning_prints_to_stderr(
        self, capsys: pytest.CaptureFixture[str], github_actions: bool
    ) -> None:
        with mock.patch("bake.ui.console.bake_settings") as mock_settings:
            mock_settings.github_actions = github_actions
            console.warning("File not found")
            captured = capsys.readouterr()
            assert get_warning_label(github_actions) in captured.err
            assert "File not found" in captured.err
            assert captured.out == ""


class TestError:
    @pytest.mark.parametrize("github_actions", [False, True])
    def test_error_prints_to_stderr(
        self, capsys: pytest.CaptureFixture[str], github_actions: bool
    ) -> None:
        with mock.patch("bake.ui.console.bake_settings") as mock_settings:
            mock_settings.github_actions = github_actions
            console.error("Failed to connect")
            captured = capsys.readouterr()
            assert get_error_label(github_actions) in captured.err
            assert "Failed to connect" in captured.err
            assert captured.out == ""


class TestOutputToCorrectStream:
    @pytest.mark.parametrize(
        "func_name,stream_name",
        [
            ("echo", "out"),
            ("info", "err"),
            ("start", "err"),
            ("end", "err"),
            ("success", "err"),
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
        assert "=" in captured.err  # bold line character
        assert "-" in captured.err  # thin line character


class TestThinLine:
    def test_thin_line_uses_dash_char(self, capsys: pytest.CaptureFixture[str]) -> None:
        console.thin_line("stdout")
        captured = capsys.readouterr()
        assert "stdout" in captured.err
        assert "-" in captured.err
        assert captured.out == ""


class TestBlock:
    def test_block_default_close_has_end_label(self, capsys: pytest.CaptureFixture[str]) -> None:
        with console.block("Deploy"):
            console.err.print("body")
        captured = capsys.readouterr()
        assert "END" in captured.err
        assert "Deploy" in captured.err
        assert captured.out == ""

    def test_block_inline_mode_puts_title_in_rule(self, capsys: pytest.CaptureFixture[str]) -> None:
        with console.block("lint", title_mode="inline"):
            console.err.print("body")
        captured = capsys.readouterr()
        assert "lint" in captured.err
        assert captured.out == ""


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
    assert console.ARROW in captured.err
    assert captured.out == ""


def test_script_block_falls_back_to_dedent_on_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with mock.patch("beautysh.BashFormatter") as mock_formatter:
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


def test_github_action_add_mask_prints_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    with mock.patch("bake.ui.console.bake_settings") as mock_settings:
        mock_settings.github_actions = True
        console.github_action_add_mask("my-secret-token")
        captured = capsys.readouterr()
        assert "::add-mask::my-secret-token" in captured.out
        assert captured.err == ""


class TestFlush:
    def test_flush_calls_both_consoles(self) -> None:
        with (
            mock.patch.object(console.out.file, "flush") as mock_out_flush,
            mock.patch.object(console.err.file, "flush") as mock_err_flush,
        ):
            console.flush()
        mock_out_flush.assert_called_once()
        mock_err_flush.assert_called_once()


def test_github_action_add_mask_does_nothing_when_not_github_actions(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with mock.patch("bake.ui.console.bake_settings") as mock_settings:
        mock_settings.github_actions = False
        console.github_action_add_mask("my-secret-token")
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""
