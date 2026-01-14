from typing import Annotated, Literal

import typer

from bake.cli.common.context import Context
from bake.manage.run_uv import run_uv_add, run_uv_lock, run_uv_pip, run_uv_sync
from bake.ui import console
from bake.utils.exceptions import BakebookError, PythonNotFoundError

PipCommand = Literal[
    "compile",
    "sync",
    "install",
    "uninstall",
    "freeze",
    "list",
    "show",
    "tree",
    "check",
]


def pip(
    ctx: Context,
    command: Annotated[
        PipCommand,
        typer.Argument(help="UV pip subcommand"),
    ],
) -> None:
    """
    This runs `[bold cyan]uv pip <command> <args> --python <bakefile-python-path>[/bold cyan]`

    For complete docs: `[cyan]uv pip --help[/cyan]`
    """
    bakefile_path = ctx.obj.bakefile_path
    try:
        cmd = [command, *ctx.args]
        result = run_uv_pip(bakefile_path=bakefile_path, cmd=cmd, dry_run=ctx.obj.dry_run)
        raise typer.Exit(result.returncode)
    except (PythonNotFoundError, BakebookError) as e:
        console.error(str(e))
        raise typer.Exit(code=1) from None


def add(ctx: Context) -> None:
    """
    This runs `[bold cyan]uv add --script bakefile.py <args>[/bold cyan]`

    Requires PEP 723 inline metadata.

    To add metadata: `[cyan]bakefile add-inline[/cyan]`
    For project-level deps: `[cyan]uv add[/cyan]`
    For complete docs: `[cyan]uv add --help[/cyan]`

    Examples:
        bakefile add requests typer
        bakefile add "requests>=2.32.0" --dev
    """
    bakefile_path = ctx.obj.bakefile_path
    args = ctx.args

    try:
        result = run_uv_add(bakefile_path=bakefile_path, cmd=args, dry_run=ctx.obj.dry_run)
        raise typer.Exit(result.returncode)
    except (PythonNotFoundError, BakebookError) as e:
        console.error(str(e))
        raise typer.Exit(code=1) from None


def lock(
    ctx: Context,
    upgrade: Annotated[
        bool,
        typer.Option("--upgrade", "-U", help="Upgrade package dependencies"),
    ] = False,
) -> None:
    """
    This runs `[bold cyan]uv lock --script bakefile.py <args>[/bold cyan]`

    Requires PEP 723 inline metadata.

    To add metadata: `[cyan]bakefile add-inline[/cyan]`
    For project-level deps: `[cyan]uv lock[/cyan]`
    For complete docs: `[cyan]uv lock --help[/cyan]`

    Examples:
        bakefile lock
        bakefile lock --upgrade
        bakefile lock --no-build
    """
    bakefile_path = ctx.obj.bakefile_path
    args = list(ctx.args)

    if upgrade:
        args.append("--upgrade")

    try:
        result = run_uv_lock(bakefile_path=bakefile_path, cmd=args, dry_run=ctx.obj.dry_run)
        raise typer.Exit(result.returncode)
    except (PythonNotFoundError, BakebookError) as e:
        console.error(str(e))
        raise typer.Exit(code=1) from None


def sync(
    ctx: Context,
    upgrade: Annotated[
        bool,
        typer.Option("--upgrade", "-U", help="Upgrade package dependencies"),
    ] = False,
    reinstall: Annotated[
        bool,
        typer.Option("--reinstall", help="Reinstall all packages"),
    ] = False,
) -> None:
    """
    This runs `[bold cyan]uv sync --script bakefile.py <args>[/bold cyan]`

    Requires PEP 723 inline metadata.

    To add metadata: `[cyan]bakefile add-inline[/cyan]`
    For project-level deps: `[cyan]uv sync[/cyan]`
    For complete docs: `[cyan]uv sync --help[/cyan]`

    Examples:
        bakefile sync
        bakefile sync --upgrade
        bakefile sync --reinstall
        bakefile sync --frozen
        bakefile sync --no-dev
        bakefile sync --no-build
    """
    bakefile_path = ctx.obj.bakefile_path
    args = list(ctx.args)

    if upgrade:
        args.append("--upgrade")
    if reinstall:
        args.append("--reinstall")

    try:
        result = run_uv_sync(bakefile_path=bakefile_path, cmd=args, dry_run=ctx.obj.dry_run)
        raise typer.Exit(result.returncode)
    except (PythonNotFoundError, BakebookError) as e:
        console.error(str(e))
        raise typer.Exit(code=1) from None
