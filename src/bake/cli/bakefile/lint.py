from typing import Annotated

import typer

from bake.cli.common.context import Context
from bake.manage.find_python import find_python_path
from bake.manage.lint import run_ruff_check, run_ruff_format, run_ty_check
from bake.ui import console


def lint(
    ctx: Context,
    only_bakefile: Annotated[
        bool,
        typer.Option("--only-bakefile", "-b", help="Only lint the bakefile, not entire project"),
    ] = False,
    ruff_format: Annotated[
        bool,
        typer.Option("--ruff-format/--no-ruff-format", show_default=False),
    ] = True,
    ruff_check: Annotated[
        bool,
        typer.Option("--ruff-check/--no-ruff-check", show_default=False),
    ] = True,
    ty_check: Annotated[
        bool,
        typer.Option("--ty/--no-ty", show_default=False),
    ] = True,
) -> None:
    """
    Quick and strict lint your bakefile.py.

    Simple way to ensure your bakefile follows standard formatting
    and type safety best practices. By default, also lints all Python
    files in your project. For advanced linter configuration, use
    ruff and ty directly.

    By default, runs: ruff format, ruff check, ty check

    Examples:
        bakefile lint              # Lint bakefile.py and all Python files
        bakefile lint -b           # Lint only bakefile.py
        bakefile lint --no-ty      # Skip type checking
    """
    bakefile_path = ctx.obj.bakefile_path
    if bakefile_path is None or not bakefile_path.exists():
        console.error("Bakefile not found. Run 'bakefile init' first.")
        raise typer.Exit(code=1)

    if not any([ruff_format, ruff_check, ty_check]):
        console.warning("All linters disabled. Nothing to do.")
        raise typer.Exit(code=0)

    try:
        if ruff_format:
            run_ruff_format(
                bakefile_path, only_bakefile=only_bakefile, check=True, dry_run=ctx.obj.dry_run
            )

        if ruff_check:
            run_ruff_check(
                bakefile_path, only_bakefile=only_bakefile, check=True, dry_run=ctx.obj.dry_run
            )

        if ty_check:
            python_path = find_python_path(bakefile_path)
            run_ty_check(
                bakefile_path,
                python_path,
                only_bakefile=only_bakefile,
                check=True,
                dry_run=ctx.obj.dry_run,
            )
    except typer.Exit as e:
        if e.exit_code != 0:
            console.error("Linting failed.")
            raise typer.Exit(code=e.exit_code) from e
