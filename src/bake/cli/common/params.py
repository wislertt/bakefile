from pathlib import Path
from typing import Annotated

import typer

from bake.cli.utils.version import version_callback


def validate_file_name(value: str) -> str:
    """Validate file name for --file-name option."""
    if "/" in value or "\\" in value:
        raise typer.BadParameter(f"File name must not contain path separators: {value}")
    if not value.endswith(".py"):
        raise typer.BadParameter(f"File name must end with .py: {value}")
    return value


def verbosity_callback(
    _ctx: typer.Context, _param: typer.CallbackParam, value: int | None
) -> int | None:
    """Validate verbosity level (max 3)."""
    if value is not None and (value < 0 or value > 3):
        raise typer.BadParameter("Maximum verbosity is -vvv")
    return value


# ==========================================================
# Bakefile CLI Parameters
# ==========================================================
ChdirOption = Annotated[
    Path,
    typer.Option(
        "-C",
        "--chdir",
        help="Change directory before running",
    ),
]
FileNameOption = Annotated[
    str,
    typer.Option(
        "--file-name",
        "-f",
        help="Name of bakefile.py",
        callback=validate_file_name,
    ),
]
BakebookNameOption = Annotated[
    str, typer.Option("--book-name", "-b", help="Name of bakebook object to retrieve")
]
VersionOption = Annotated[
    bool,
    typer.Option(
        "--version",
        help="Show version",
        callback=version_callback,
        is_eager=True,
    ),
]
IsChainCommandsOption = Annotated[bool, typer.Option("--chain", "-c", help="Chain commands")]
RemainingArgsArgument = Annotated[list[str] | None, typer.Argument()]

VerbosityOption = Annotated[
    int | None,
    typer.Option(
        "-v",
        "--verbose",
        envvar="BAKE_LOG_VERBOSITY",
        help="Increase verbosity (-v for warning, -vv for info, -vvv for debug)",
        count=True,
        callback=verbosity_callback,
    ),
]
DryRunOption = Annotated[
    bool,
    typer.Option("-n", "--dry-run", help="Dry run (show what would be done without executing)"),
]
BakeLogOption = Annotated[
    str | None,
    typer.Option(
        "--bake-log",
        envvar="BAKE_LOG",
        help="Log level configuration (e.g., 'warning,bake=debug,bakelib=debug')",
    ),
]
BakeLogPrettyOption = Annotated[
    bool,
    typer.Option(
        "--log-pretty/--no-log-pretty",
        envvar="BAKE_LOG_PRETTY",
        help="Use pretty log format (vs JSON)",
    ),
]

# ==========================================================
# Bakefile Local CLI Frequently Used Params
# ==========================================================
ForceOption = Annotated[
    bool | None, typer.Option("--force/--no-force", "-f", help="Force execution")
]
