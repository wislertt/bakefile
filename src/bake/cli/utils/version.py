import platform
import re
from collections.abc import Callable
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import typer
from rich.text import Text

from bake.ui import console

_VERSION_RE = re.compile(
    r"^(?P<label>\S+) (?P<version>\S+) from (?P<path>.+) \(python (?P<pyver>[^)]+)\)$"
)

_VERSION_STYLE = "bold cyan"
_PATH_STYLE = "magenta"


def _get_version() -> str:
    try:
        return version("bakefile")
    except PackageNotFoundError:
        return "0.0.0"


def _bake_root() -> Path:
    import bake

    return Path(bake.__file__).resolve().parent


def _format_version(label: str) -> str:
    return f"{label} {_get_version()} from {_bake_root()} (python {platform.python_version()})"


def _parse_version_string(raw: str) -> dict[str, str] | None:
    match = _VERSION_RE.match(raw.strip())
    return match.groupdict() if match is not None else None


def _colorize_version_parts(label: str, ver: str, path: str, pyver: str) -> Text:
    return Text.assemble(
        (f"{label} ", ""),
        (ver, _VERSION_STYLE),
        (" from ", ""),
        (path, _PATH_STYLE),
        (f" (python {pyver})", ""),
    )


def _colorize_version_string(raw: str) -> Text | None:
    parts = _parse_version_string(raw)
    if parts is None:
        return None
    return _colorize_version_parts(parts["label"], parts["version"], parts["path"], parts["pyver"])


def make_version_callback(label: str) -> Callable[[bool], None]:
    def _version_callback(value: bool) -> None:
        if value:
            raw = _format_version(label)
            console.out.print(_colorize_version_string(raw) or raw)
            raise typer.Exit()

    return _version_callback
