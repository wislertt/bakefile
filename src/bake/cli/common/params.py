from pathlib import Path
from typing import Annotated

import typer

from bake.cli.common.callback import validate_file_name_callback
from bake.cli.utils.version import version_callback


def verbosity_callback(_ctx: typer.Context, _param: typer.CallbackParam, value: int) -> int:
    """Validate verbosity level (max 2)."""
    if value > 2:
        raise typer.BadParameter("Maximum verbosity is -vv")
    return value


# ==========================================================
# Bakefile CLI Parameters
# ==========================================================
chdir_option = Annotated[
    Path,
    typer.Option(
        "-C",
        "--chdir",
        help="Change directory before running",
    ),
]
file_name_option = Annotated[
    str,
    typer.Option(
        "--file-name",
        "-f",
        help="Path to bakefile.py",
        callback=validate_file_name_callback,
    ),
]
bakebook_name_option = Annotated[
    str, typer.Option("--book-name", "-b", help="Name of bakebook object to retrieve")
]
version_option = Annotated[
    bool,
    typer.Option(
        "--version",
        help="Show version",
        callback=version_callback,
        is_eager=True,
    ),
]
is_chain_commands_option = Annotated[bool, typer.Option("--chain", "-c", help="Chain commands")]
remaining_args_argument = Annotated[list[str] | None, typer.Argument()]

verbosity_option = Annotated[
    int,
    typer.Option(
        "-v",
        "--verbose",
        help="Increase verbosity (-v for info, -vv for debug)",
        count=True,
        callback=verbosity_callback,
    ),
]
dry_run_option = Annotated[
    bool,
    typer.Option("-n", "--dry-run", help="Dry run (show what would be done without executing)"),
]

# ==========================================================
# Bakefile Local CLI Frequently Used Params
# ==========================================================
force_option = Annotated[
    bool | None, typer.Option("--force/--no-force", "-f", help="Force execution")
]
