import typer

from bake.cli.common.context import Context
from bake.manage.find_python import find_python_path
from bake.ui import console
from bake.utils.exceptions import PythonNotFoundError


def find_python(
    ctx: Context,
) -> None:
    """Find the Python interpreter path for the bakefile.py project."""
    try:
        python_path = find_python_path(ctx.obj.bakefile_path)
        console.echo(python_path.as_posix())
    except PythonNotFoundError as e:
        console.error(str(e))
        raise typer.Exit(code=1) from None
