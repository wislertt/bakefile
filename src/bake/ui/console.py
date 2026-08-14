import sys
import textwrap
from contextlib import contextmanager
from typing import Any, Literal

import rich
import rich.style
from rich.console import Console as RichConsole
from rich.console import JustifyMethod, OverflowMethod
from rich.rule import Rule
from rich.text import Text

from bake.ui.style import BLUE, BOLD_BLUE, BOLD_GREEN
from bake.utils.settings import bake_settings

OVERFLOW_DEFAULT = "ignore"
CROP_DEFAULT = False


class Console(RichConsole):
    def print(
        self,
        *objects: Any,
        sep: str = " ",
        end: str = "\n",
        style: str | rich.style.Style | None = None,
        justify: JustifyMethod | None = None,
        overflow: OverflowMethod | None = OVERFLOW_DEFAULT,
        no_wrap: bool | None = None,
        emoji: bool | None = None,
        markup: bool | None = None,
        highlight: bool | None = None,
        width: int | None = None,
        height: int | None = None,
        crop: bool = CROP_DEFAULT,
        soft_wrap: bool | None = None,
        new_line_start: bool = False,
    ) -> None:
        return super().print(
            *objects,
            sep=sep,
            end=end,
            style=style,
            justify=justify,
            overflow=overflow,
            no_wrap=no_wrap,
            emoji=emoji,
            markup=markup,
            highlight=highlight,
            width=width,
            height=height,
            crop=crop,
            soft_wrap=soft_wrap,
            new_line_start=new_line_start,
        )


_FORCE_TERMINAL_DEFAULT = (
    # Force terminal mode in GitHub Actions to enable ANSI color output.
    # Without this, rich auto-detects no TTY and disables colors.
    # By default, use None for auto-detection (preserves normal behavior).
    True if bake_settings.github_actions else None
)


_LEGACY_WINDOWS_DEFAULT = (
    # Force disable legacy Windows mode in GitHub Actions to use ANSI codes.
    # GitHub Actions Windows runners support ANSI, but rich may auto-detect legacy mode.
    False if bake_settings.github_actions else None
)

out = Console(
    stderr=False,
    force_terminal=_FORCE_TERMINAL_DEFAULT,
    legacy_windows=_LEGACY_WINDOWS_DEFAULT,
)
err = Console(
    stderr=True,
    force_terminal=_FORCE_TERMINAL_DEFAULT,
    legacy_windows=_LEGACY_WINDOWS_DEFAULT,
)
plain_out = Console(no_color=True, stderr=False)
plain_err = Console(no_color=True, stderr=True)


UNICODE_ENCODINGS = {"utf-8", "utf-16", "utf-32", "utf-16-le", "utf-16-be"}


def _supports_unicode() -> bool:
    return sys.stdout.encoding.lower() in UNICODE_ENCODINGS


ARROW = "❯" if _supports_unicode() else ">"  # noqa: RUF001


def _format_prefix(
    console_obj: Console,
    emoji: str | None,
    label: str,
    style: str,
    message: str,
) -> str:
    formatted_label = f"[{label}]" if console_obj.no_color or out.color_system is None else label

    # Strip emoji/unicode in non-UTF contexts (e.g., Windows CI) to avoid encoding issues
    emoji_str = ""
    if emoji and _supports_unicode():
        emoji_str = emoji + " "

    return f"[{style}]{emoji_str}{formatted_label}[/{style}] {message}"


def _get_console(stderr: bool) -> Console:
    return err if stderr else out


def prefix(
    message: str,
    *,
    emoji: str | None = None,
    label: str = "INFO",
    style: str = BOLD_BLUE,
    stderr: bool = False,
    **kwargs,
) -> None:
    target = _get_console(stderr)
    target.print(
        _format_prefix(target, emoji=emoji, label=label, style=style, message=message), **kwargs
    )


def success(message: str, *, stderr: bool = True, **kwargs) -> None:
    prefix(
        message,
        emoji=":white_check_mark:",
        label="SUCCESS",
        style=BOLD_GREEN,
        stderr=stderr,
        **kwargs,
    )


def info(message: str, *, label: str = "INFO", stderr: bool = True, **kwargs) -> None:
    prefix(message, emoji=None, label=label, style=BLUE, stderr=stderr, **kwargs)


def start(message: str, *, stderr: bool = True, **kwargs) -> None:
    info(f"{message}...", label="START", stderr=stderr, **kwargs)


def end(message: str, *, stderr: bool = True, **kwargs) -> None:
    info(message, label="END", stderr=stderr, **kwargs)


def echo(message: Any, *, stderr: bool = False, **kwargs) -> None:
    _get_console(stderr).print(message, **kwargs)


def cmd(cmd_str: str, *, stderr: bool = True, **kwargs) -> None:
    arrow_text = Text(ARROW, style=BOLD_GREEN)
    cmd_text = Text(f"{cmd_str}")
    _get_console(stderr).print(arrow_text, cmd_text, **kwargs)


BLOCK_WIDTH = 70


def _block_width() -> int:
    return min(BLOCK_WIDTH, err.size.width)


def line(text: str = "", *, char: str = "=", style: str = BOLD_GREEN) -> None:
    err.print(Rule(text, characters=char, style=style), width=_block_width())


def thin_line(text: str = "", *, char: str = "-", style: str = "dim") -> None:
    line(text, char=char, style=style)


@contextmanager
def block(
    title: str,
    *,
    line_style: str = BOLD_GREEN,
    title_style: str = "bold",
    title_mode: Literal["framed", "inline"] = "framed",
    start_label: str = "",
    end_label: str = "END",
    end_title: bool = True,
    outer_line_char: str = "=",
    inner_line_char: str = "-",
):
    styled_title = f"[{title_style}]{title}[/{title_style}]"
    start = f"[{BLUE}]{start_label}[/{BLUE}] {styled_title}" if start_label else styled_title
    if end_title:
        end = f"[{BLUE}]{end_label}[/{BLUE}] {styled_title}" if end_label else styled_title
    else:
        end = ""
    if title_mode == "inline":
        line(start, char=outer_line_char, style=line_style)
    else:  # framed
        line(char=outer_line_char, style=line_style)
        err.print(start)
        line(char=inner_line_char, style=line_style)
    try:
        yield
    finally:
        line(end, char=outer_line_char, style=line_style)


def script_block(title: str, script: str, **kwargs) -> None:
    # Lazy import: beautysh adds a StreamHandler to logging.root at import time
    from beautysh import BashFormatter

    formatter = BashFormatter()
    formatted, error = formatter.beautify_string(script)

    if error:
        formatted = textwrap.dedent(script)

    with block(title, end_title=False):
        err.print(formatted, highlight=False, **kwargs)


def warning(message: str, *, stderr: bool = True, **kwargs) -> None:
    if bake_settings.github_actions:
        _get_console(stderr).print(f"::warning::{message}", **kwargs)
    else:
        prefix(
            message,
            emoji=":warning-emoji: ",
            label="WARNING",
            style="bold yellow",
            stderr=stderr,
            **kwargs,
        )


def error(message: str, *, stderr: bool = True, **kwargs) -> None:
    if bake_settings.github_actions:
        _get_console(stderr).print(f"::error::{message}", **kwargs)
    else:
        prefix(message, emoji=":x:", label="ERROR", style="bold red", stderr=stderr, **kwargs)


def flush() -> None:
    out.file.flush()
    err.file.flush()


def github_action_add_mask(value: str, **kwargs) -> None:
    if bake_settings.github_actions:
        out.print(f"::add-mask::{value}", **kwargs)
