import sys
import textwrap
from typing import Any

from beautysh import BashFormatter
from rich.console import Console

from bake.utils.settings import bake_settings

out = Console(stderr=False)
err = Console(stderr=True)

BOLD_GREEN = "bold green"


def _format_prefix(
    console_obj: Console,
    emoji: str | None,
    label: str,
    style: str,
    message: str,
) -> str:
    formatted_label = f"[{label}]" if console_obj.no_color or out.color_system is None else label

    # Strip emoji in non-terminal contexts (e.g., CI) to avoid encoding issues
    emoji_str = ""
    if emoji and sys.stdout.isatty():
        emoji_str = emoji + " "

    return f"[{style}]{emoji_str}{formatted_label}[/{style}] {message}"


def prefix_out(
    message: str,
    emoji: str | None = None,
    label: str = "INFO",
    style: str = "bold blue",
    **kwargs,
) -> None:
    out.print(_format_prefix(out, emoji=emoji, label=label, style=style, message=message), **kwargs)


def prefix_err(
    message: str,
    emoji: str | None = None,
    label: str = "INFO",
    style: str = "bold blue",
    **kwargs,
) -> None:
    err.print(_format_prefix(err, emoji=emoji, label=label, style=style, message=message), **kwargs)


def success(message: str, **kwargs) -> None:
    prefix_out(
        emoji=":white_check_mark:",
        label="SUCCESS",
        style=BOLD_GREEN,
        message=message,
        **kwargs,
    )


def echo(message: Any, **kwargs) -> None:
    out.print(message, **kwargs)


def cmd(cmd_str: str, **kwargs) -> None:
    err.print(f"[{BOLD_GREEN}]❯[/{BOLD_GREEN}] [default]{cmd_str}[/default]", **kwargs)  # noqa: RUF001


def script_block(title: str, script: str, **kwargs) -> None:
    formatter = BashFormatter()
    formatted, error = formatter.beautify_string(script)

    if error:
        formatted = textwrap.dedent(script)

    terminal_width: int = err.size.width
    width = min(70, terminal_width)
    bold_line = "━" * width
    thin_line = "─" * width

    err.print(bold_line, style=BOLD_GREEN)
    err.print(title, style="bold")
    err.print(thin_line, style=BOLD_GREEN)
    err.print(formatted, highlight=False, **kwargs)
    err.print(bold_line, style=BOLD_GREEN)


def warning(message: str, **kwargs) -> None:
    if bake_settings.github_actions:
        err.print(f"::warning::{message}", **kwargs)
    else:
        prefix_err(
            emoji=":warning-emoji: ",
            label="WARNING",
            style="bold yellow",
            message=message,
            **kwargs,
        )


def error(message: str, **kwargs) -> None:
    if bake_settings.github_actions:
        err.print(f"::error::{message}", **kwargs)
    else:
        prefix_err(emoji=":x:", label="ERROR", style="bold red", message=message, **kwargs)
