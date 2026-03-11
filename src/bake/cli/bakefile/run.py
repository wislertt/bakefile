import logging
from pathlib import Path

import typer

from bake.cli.common.context import Context
from bake.manage.find_python import find_python_path
from bake.ui import console
from bake.ui.run.run import run as _run
from bake.utils.exceptions import BakebookError, PythonNotFoundError

logger = logging.getLogger(__name__)


def run(ctx: Context) -> None:
    """
    This runs `[bold cyan]python <args>[/bold cyan]` using bakefile's Python environment.

    Execute commands using the bakefile's Python environment.

    - If first arg is a file that exists, runs as script: `python script.py`
    - Otherwise, runs as module: `python -m module`

    Examples:
        bakefile run test.py
        bakefile run ruff check src/
        bakefile run pytest tests/
        bakefile run mymodule --option value
    """
    if not ctx.args or ctx.args[0] in ("--help"):
        typer.echo(ctx.get_help())
        raise typer.Exit(code=0)

    bakefile_path: Path | None = ctx.obj.bakefile_path

    try:
        python_path = find_python_path(bakefile_path)
    except (PythonNotFoundError, BakebookError) as e:
        console.error(str(e))
        raise typer.Exit(code=1) from None

    logger.debug(f"Using bakefile Python: {python_path}")

    first_arg = ctx.args[0]
    first_arg_path = Path(first_arg)

    if first_arg_path.is_file():
        script_path = first_arg_path.resolve()
        remaining_args = ctx.args[1:]
        cmd = [str(python_path), str(script_path), *remaining_args]
        echo_cmd = f"python {first_arg} {' '.join(remaining_args)}"
        cwd = script_path.parent
    else:
        cmd = [str(python_path), "-m", *ctx.args]
        echo_cmd = f"python -m {' '.join(ctx.args)}"
        cwd = bakefile_path.parent if bakefile_path else None

    _run(
        cmd,
        capture_output=True,
        stream=True,
        check=True,
        echo=True,
        cwd=cwd,
        dry_run=ctx.obj.dry_run,
        echo_cmd=echo_cmd,
    )
