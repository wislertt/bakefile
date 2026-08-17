import sys
import textwrap
from contextlib import contextmanager
from typing import Any, Literal

import rich
import rich.style
from rich.console import Console as RichConsole
from rich.console import JustifyMethod, OverflowMethod
from rich.emoji import Emoji
from rich.rule import Rule
from rich.text import Text
from typing_extensions import NotRequired, TypedDict, Unpack

from bake.ui.style import BLUE, BOLD_BLUE, BOLD_GREEN
from bake.utils.settings import bake_settings

OVERFLOW_DEFAULT = "ignore"
CROP_DEFAULT = False

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

UNICODE_ENCODINGS = {"utf-8", "utf-16", "utf-32", "utf-16-le", "utf-16-be"}


def _supports_unicode() -> bool:
    return sys.stdout.encoding.lower() in UNICODE_ENCODINGS


ARROW = "❯" if _supports_unicode() else ">"  # noqa: RUF001

BLOCK_WIDTH = 70

__all__ = [
    "block",
    "cmd",
    "echo",
    "end",
    "err",
    "error",
    "flush",
    "github_action_add_mask",
    "info",
    "line",
    "out",
    "plain_err",
    "plain_out",
    "prefix",
    "script_block",
    "start",
    "success",
    "thin_line",
    "warning",
]


class PrintKwargs(TypedDict):
    # Keyword arguments forwarded to RichConsole.print; drift-guarded by
    # tests/unit/bake/ui/test_console.py. Own params never shadow these names:
    # chrome styling uses label_style/arrow_style, shortcodes use emoji_code.
    sep: NotRequired[str]
    end: NotRequired[str]
    justify: NotRequired[JustifyMethod | None]
    overflow: NotRequired[OverflowMethod | None]
    no_wrap: NotRequired[bool | None]
    markup: NotRequired[bool | None]
    highlight: NotRequired[bool | None]
    width: NotRequired[int | None]
    height: NotRequired[int | None]
    crop: NotRequired[bool]
    soft_wrap: NotRequired[bool | None]
    new_line_start: NotRequired[bool]
    style: NotRequired[str | rich.style.Style | None]
    emoji: NotRequired[bool | None]


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


def _replace_emoji(emoji_code: str) -> str:
    # Shortcode typos fail fast instead of rendering literally; literal glyphs pass through.
    replaced = Emoji.replace(emoji_code)
    if emoji_code.startswith(":") and emoji_code.endswith(":") and replaced == emoji_code:
        raise ValueError(f"unknown emoji code: {emoji_code!r}")
    return replaced


def _get_prefix(console: Console, emoji_code: str | None, label: str, label_style: str) -> Text:
    formatted_label = f"[{label}]" if console.no_color or console.color_system is None else label

    # Strip emoji/unicode in non-UTF contexts (e.g., Windows CI) to avoid encoding issues
    emoji_str = ""
    if emoji_code and _supports_unicode():
        emoji_str = _replace_emoji(emoji_code) + " "

    # Text bypasses rich markup/highlight kwargs, so label styling is independent.
    # no_color consoles still render attributes (e.g. bold), so drop the style.
    text_style = "" if console.no_color else label_style
    return Text(f"{emoji_str}{formatted_label}", style=text_style)


def _get_console(stderr: bool, no_color: bool = False) -> Console:
    if no_color:
        return plain_err if stderr else plain_out
    return err if stderr else out


def prefix(
    message: str,
    *,
    label: str,
    emoji_code: str | None = None,
    label_style: str = BOLD_BLUE,
    stderr: bool = True,
    no_color: bool = False,
    **kwargs: Unpack[PrintKwargs],
) -> None:
    console = _get_console(stderr, no_color=no_color)
    if no_color:
        kwargs.setdefault("highlight", False)
        kwargs.setdefault("markup", False)
    label_text = _get_prefix(console, emoji_code=emoji_code, label=label, label_style=label_style)
    console.print(label_text, message, **kwargs)


def success(
    message: str,
    *,
    stderr: bool = True,
    no_color: bool = False,
    **kwargs: Unpack[PrintKwargs],
) -> None:
    prefix(
        message,
        emoji_code=":white_check_mark:",
        label="SUCCESS",
        label_style=BOLD_GREEN,
        stderr=stderr,
        no_color=no_color,
        **kwargs,
    )


def info(
    message: str,
    *,
    label: str = "INFO",
    stderr: bool = True,
    no_color: bool = False,
    **kwargs: Unpack[PrintKwargs],
) -> None:
    prefix(
        message,
        emoji_code=None,
        label=label,
        label_style=BLUE,
        stderr=stderr,
        no_color=no_color,
        **kwargs,
    )


def start(
    message: str,
    *,
    stderr: bool = True,
    no_color: bool = False,
    **kwargs: Unpack[PrintKwargs],
) -> None:
    info(f"{message}...", label="START", stderr=stderr, no_color=no_color, **kwargs)


def end(
    message: str,
    *,
    stderr: bool = True,
    no_color: bool = False,
    **kwargs: Unpack[PrintKwargs],
) -> None:
    info(message, label="END", stderr=stderr, no_color=no_color, **kwargs)


def echo(
    message: Any, *, stderr: bool = False, no_color: bool = False, **kwargs: Unpack[PrintKwargs]
) -> None:
    console = _get_console(stderr, no_color=no_color)
    console.print(message, **kwargs)


def cmd(
    cmd_str: str,
    *,
    arrow_style: str = BOLD_GREEN,
    stderr: bool = True,
    no_color: bool = False,
    **kwargs: Unpack[PrintKwargs],
) -> None:
    text_arrow_style = "" if no_color else arrow_style
    console = _get_console(stderr, no_color=no_color)
    console.print(Text(ARROW, style=text_arrow_style), Text(cmd_str), **kwargs)


def _block_width(console: Console) -> int:
    return min(BLOCK_WIDTH, console.size.width)


def _get_block_label(label: str, no_color: bool) -> str:
    # Labels are color-only markup; plain consoles strip color, so skip wrapping there.
    return label if no_color else f"[{BLUE}]{label}[/{BLUE}]"


def line(
    text: str = "",
    *,
    char: str = "=",
    style: str = BOLD_GREEN,
    stderr: bool = True,
    no_color: bool = False,
) -> None:
    console = _get_console(stderr, no_color=no_color)
    # Match prefix/cmd: no_color drops styles (plain consoles still render bold).
    rule_style = "" if no_color else style
    console.print(Rule(text, characters=char, style=rule_style), width=_block_width(console))


def thin_line(
    text: str = "",
    *,
    char: str = "-",
    style: str = "dim",
    stderr: bool = True,
    no_color: bool = False,
) -> None:
    line(text, char=char, style=style, stderr=stderr, no_color=no_color)


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
    stderr: bool = True,
    no_color: bool = False,
):
    console = _get_console(stderr, no_color=no_color)
    # Same no_color rule as line/prefix/cmd: skip markup so output has zero ANSI.
    styled_title = title if no_color else f"[{title_style}]{title}[/{title_style}]"
    start = (
        f"{_get_block_label(start_label, no_color)} {styled_title}" if start_label else styled_title
    )
    if end_title:
        end = (
            f"{_get_block_label(end_label, no_color)} {styled_title}" if end_label else styled_title
        )
    else:
        end = ""
    if title_mode == "inline":
        line(start, char=outer_line_char, style=line_style, stderr=stderr, no_color=no_color)
    else:  # framed
        line(char=outer_line_char, style=line_style, stderr=stderr, no_color=no_color)
        console.print(start)
        line(char=inner_line_char, style=line_style, stderr=stderr, no_color=no_color)
    try:
        yield
    finally:
        line(end, char=outer_line_char, style=line_style, stderr=stderr, no_color=no_color)


def script_block(
    title: str,
    script: str,
    *,
    stderr: bool = True,
    no_color: bool = False,
    **kwargs: Unpack[PrintKwargs],
) -> None:
    # Lazy import: beautysh adds a StreamHandler to logging.root at import time
    from beautysh import BashFormatter

    formatter = BashFormatter()
    formatted, error = formatter.beautify_string(script)

    if error:
        formatted = textwrap.dedent(script)

    if no_color:
        kwargs.setdefault("highlight", False)
        kwargs.setdefault("markup", False)
    print_kwargs: PrintKwargs = {"highlight": False}
    print_kwargs.update(kwargs)
    with block(title, end_title=False, stderr=stderr, no_color=no_color):
        console = _get_console(stderr, no_color=no_color)
        console.print(formatted, **print_kwargs)


def warning(
    message: str,
    *,
    stderr: bool = True,
    no_color: bool = False,
    **kwargs: Unpack[PrintKwargs],
) -> None:
    if bake_settings.github_actions:
        console = _get_console(stderr, no_color=no_color)
        console.print(f"::warning::{message}", **kwargs)
    else:
        prefix(
            message,
            emoji_code=":warning-emoji: ",
            label="WARNING",
            label_style="bold yellow",
            stderr=stderr,
            no_color=no_color,
            **kwargs,
        )


def error(
    message: str,
    *,
    stderr: bool = True,
    no_color: bool = False,
    **kwargs: Unpack[PrintKwargs],
) -> None:
    if bake_settings.github_actions:
        console = _get_console(stderr, no_color=no_color)
        console.print(f"::error::{message}", **kwargs)
    else:
        prefix(
            message,
            emoji_code=":x:",
            label="ERROR",
            label_style="bold red",
            stderr=stderr,
            no_color=no_color,
            **kwargs,
        )


def flush() -> None:
    out.file.flush()
    err.file.flush()


def github_action_add_mask(value: str, **kwargs: Unpack[PrintKwargs]) -> None:
    if bake_settings.github_actions:
        out.print(f"::add-mask::{value}", **kwargs)
