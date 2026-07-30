import typer

from bake.cli.common.context import Context
from bake.manage.find_python import find_python_path
from bake.ui import console
from bake.utils.exceptions import PythonNotFoundError


def find_python(
    ctx: Context,
) -> None:
    """Print the Python path that reinvoker commands switch to.

    Those commands: bake, bakefile env/export/run/lint.
    """
    try:
        python_path = find_python_path(ctx.obj.bakefile_path)
        console.echo(python_path.as_posix())
        console.err.print(
            "Reinvoked Python — run `bakefile which` for invoked-vs-reinvoked detail.",
            style="dim",
        )
    except PythonNotFoundError as e:
        console.error(str(e))
        raise typer.Exit(code=1) from None
