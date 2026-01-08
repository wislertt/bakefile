import textwrap
from typing import Any

from beautysh import BashFormatter
from rich.console import Console

out = Console(stderr=False)
err = Console(stderr=True)


def _print(
    console_obj: Console, emoji: str | None, label: str, style: str, message: str, **kwargs
) -> None:
    formatted_label = f"[{label}]" if console_obj.no_color or out.color_system is None else label

    emoji = emoji + " " if emoji else ""
    console_obj.print(f"[{style}]{emoji}{formatted_label}[/{style}] {message}", **kwargs)


def success(message: str, **kwargs) -> None:
    _print(out, ":white_check_mark:", "SUCCESS", "bold green", message, **kwargs)


def echo(message: Any, **kwargs) -> None:
    out.print(message, **kwargs)


def cmd(cmd_str: str, **kwargs) -> None:
    err.print(f"[bold green]❯[/bold green] [default]{cmd_str}[/default]", **kwargs)  # noqa: RUF001


def script_block(title: str, script: str, **kwargs) -> None:
    formatter = BashFormatter()
    formatted, error = formatter.beautify_string(script)

    if error:
        formatted = textwrap.dedent(script)

    terminal_width: int = err.size.width
    width = min(70, terminal_width)
    bold_line = "━" * width
    thin_line = "─" * width

    err.print(bold_line, style="bold green")
    err.print(title, style="bold")
    err.print(thin_line, style="bold green")
    err.print(formatted, highlight=False, **kwargs)
    err.print(bold_line, style="bold green")


def warning(message: str, **kwargs) -> None:
    _print(err, ":warning-emoji: ", "WARNING", "bold yellow", message, **kwargs)


def error(message: str, **kwargs) -> None:
    _print(err, ":x:", "ERROR", "bold red", message, **kwargs)
