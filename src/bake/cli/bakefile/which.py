import platform
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

from rich.text import Text

from bake.cli.common.context import Context
from bake.cli.common.reinvocation import detect_target_python
from bake.cli.utils.version import (
    _PATH_STYLE,
    _VERSION_STYLE,
    _colorize_version_parts,
    _get_version,
    _parse_version_string,
)
from bake.ui import console
from bake.ui.console import ARROW, BOLD_GREEN

_PROBE_MODULES: tuple[str, ...] = ("bake.cli.bake", "bake.cli.bakefile")
_REINVOKERS: tuple[str, ...] = (
    "bake",
    "bakefile env",
    "bakefile export",
)
# Commands that spawn the reinvoked Python directly (no self-reinvoke, no bakebook load).
_TARGET_PYTHON_SPAWNERS: tuple[str, ...] = (
    "bakefile run",
    "bakefile lint",
)
_TARGET_PYTHON_USERS: tuple[str, ...] = (*_REINVOKERS, *_TARGET_PYTHON_SPAWNERS)
_OTHER_SUBCOMMANDS_NOTE: tuple[str, ...] = (
    "All other bakefile subcommands use INVOKED Python:",
    "  init, venv, find_python, which, uv …",
)


def _fmt_commands(cmds: tuple[str, ...]) -> str:
    # Collapse shared prefixes into slash form, e.g. "bakefile env/export".
    bare: list[str] = []
    groups: dict[str, list[str]] = {}
    for cmd in cmds:
        prefix, _, suffix = cmd.partition(" ")
        if suffix:
            groups.setdefault(prefix, []).append(suffix)
        else:
            bare.append(cmd)
    rendered = [*bare, *(f"{prefix} {'/'.join(suffixes)}" for prefix, suffixes in groups.items())]
    return ", ".join(rendered)


class _Invoked(NamedTuple):
    python: str
    version: str
    pyver: str


def _probe_target_version_string(target: Path) -> str | None:
    for module in _PROBE_MODULES:
        result = subprocess.run(
            [str(target), "-m", module, "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            continue
        out = result.stdout.strip()
        if out:
            return out
    return None


def _version_text(lead: str, *, version: str, path: str, pyver: str) -> Text:
    text = Text(lead)
    text.append(_colorize_version_parts("bakefile", version, path, pyver))
    return text


def _invoked_line(invoked: _Invoked) -> Text:
    return _version_text(
        "Invoked Python:  ",
        version=invoked.version,
        path=invoked.python,
        pyver=invoked.pyver,
    )


def _summary_line(body: Text | str) -> Text:
    line = Text.assemble((ARROW, BOLD_GREEN), (" ", ""))
    line.append(body)
    return line


def _verdict(invoked_version: str, target_python: str, target_version: str | None) -> Text:
    count = len(_REINVOKERS)
    if target_version is None:
        body = Text.assemble(
            (f"{count} commands would reinvoke under ", ""),
            (target_python, _PATH_STYLE),
            (", but that install could not be queried.", ""),
        )
    elif target_version == invoked_version:
        body = Text.assemble(
            (f"{count} commands reinvoke to a different Python; bakefile version unchanged (", ""),
            (invoked_version, _VERSION_STYLE),
            (").", ""),
        )
    else:
        body = Text.assemble(
            (f"{count} commands reinvoke to a different Python: bakefile ", ""),
            (invoked_version, _VERSION_STYLE),
            (" (invoked) → ", ""),
            (target_version, _VERSION_STYLE),
            (" (reinvoked).", ""),
        )
    return _summary_line(body)


def _section_no_bakefile(invoked: _Invoked) -> list[Text | str]:
    return [
        "No bakefile.py found here.",
        "",
        f"Reinvoker commands ({_fmt_commands(_REINVOKERS)}) load the bakebook — with "
        "no bakefile they have nothing to load and would error.",
        "",
        f"{_fmt_commands(_TARGET_PYTHON_SPAWNERS)} resolve the bakefile's Python — "
        "with no bakefile they would error too.",
        "",
        *_OTHER_SUBCOMMANDS_NOTE,
        "",
        _invoked_line(invoked),
        _summary_line("Nothing to reinvoke."),
    ]


def _section_no_project_python(invoked: _Invoked) -> list[Text | str]:
    return [
        "Bakefile found, but no reinvoked Python could be determined.",
        "",
        f"{_fmt_commands(_TARGET_PYTHON_USERS)} need the bakefile's Python — they "
        "would error until one exists.",
        "Fix: `bakefile venv` (project) or `bakefile add-inline` (standalone).",
        "",
        *_OTHER_SUBCOMMANDS_NOTE,
        "",
        _invoked_line(invoked),
        _summary_line("Nothing to reinvoke."),
    ]


def _section_unified(invoked: _Invoked) -> list[Text | str]:
    return [
        "All commands run on the same Python (invoked == reinvoked):",
        "",
        _version_text(
            "  ",
            version=invoked.version,
            path=invoked.python,
            pyver=invoked.pyver,
        ),
        "",
        _summary_line(
            f"No reinvoke — {_fmt_commands(_TARGET_PYTHON_USERS)}, and all other "
            "subcommands use this Python."
        ),
    ]


def _section_switch(invoked: _Invoked, target: Path) -> list[Text | str]:
    target_python = str(target)
    target_raw = _probe_target_version_string(target)
    target_parts = _parse_version_string(target_raw) if target_raw is not None else None
    target_version = target_parts["version"] if target_parts else None
    target_pyver = target_parts["pyver"] if target_parts else ""

    parts: list[Text | str] = [
        Text.assemble(
            "Reinvokes under a different Python ",
            ("(re-runs itself under it; loads the bakebook)", "dim"),
            ":",
        ),
        "",
        *[f"  {cmd}" for cmd in _REINVOKERS],
        "",
        Text.assemble(
            "Spawns the reinvoked Python ",
            ("(runs your code under it; no self-reinvoke, no bakebook)", "dim"),
            ":",
        ),
        "",
        *[f"  {cmd}" for cmd in _TARGET_PYTHON_SPAWNERS],
        "",
        *_OTHER_SUBCOMMANDS_NOTE,
        "",
        _invoked_line(invoked),
    ]
    if target_parts is not None:
        parts.append(
            _version_text(
                "Reinvoked Python:  ",
                version=target_version or "",
                path=target_python,
                pyver=target_pyver,
            )
        )
    else:
        parts.append(f"Reinvoked Python:  {target_python}    (unable to query)")
    parts.append("")
    parts.append(_verdict(invoked.version, target_python, target_version))
    return parts


def _emit(parts: list[Text | str]) -> None:
    # Render as one Text so a single highlight=False protects all plain prose
    # from Rich's ReprHighlighter, while explicit version/path styles survive.
    acc = Text()
    for part in parts:
        if len(acc):
            acc.append("\n")
        acc.append(part)
    console.echo(acc, highlight=False)


def _print_which(bakefile_path: Path | None) -> None:
    invoked = _Invoked(
        python=sys.executable,
        version=_get_version(),
        pyver=platform.python_version(),
    )

    detected = detect_target_python(bakefile_path)
    if detected.status == "no_bakefile":
        section = _section_no_bakefile(invoked)
    elif detected.status == "no_project_python":
        section = _section_no_project_python(invoked)
    elif detected.status == "unified":
        section = _section_unified(invoked)
    else:
        assert detected.python is not None  # "switch" always carries a target
        section = _section_switch(invoked, detected.python)

    _emit(["bakefile which — which Python each command uses", "", *section])


def which(ctx: Context) -> None:
    """Diagnose which Python each bake/bakefile command uses, by whether it loads the bakebook."""
    _print_which(ctx.obj.bakefile_path)
