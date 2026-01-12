import typer

from bake.cli.common.context import Context
from bake.manage.add_inline import add_inline_metadata
from bake.ui import console, style
from bake.utils.exceptions import BakebookError


def add_inline(
    ctx: Context,
) -> None:
    """Add PEP 723 inline metadata to bakefile.py.

    For non-Python projects without pyproject.toml for dependency management.
    """
    if ctx.obj.bakefile_path is None or not ctx.obj.bakefile_path.exists():
        console.error(
            f"Bakefile not found at {ctx.obj.bakefile_path}. "
            f"Run {style.code('bakefile init --inline')} to create one."
        )
        raise typer.Exit(code=1)

    try:
        add_inline_metadata(ctx.obj.bakefile_path)
    except BakebookError as e:
        console.error(str(e))
        raise typer.Exit(code=1) from None

    console.success(f"Successfully added PEP 723 inline metadata to {ctx.obj.bakefile_path}")
