from typing import Annotated

import typer

from bake.bakebook.get import (
    resolve_bakefile_path,
)
from bake.cli.common.context import Context
from bake.cli.common.params import force_option
from bake.manage.add_inline import add_inline_metadata
from bake.manage.write_bakefile import write_bakefile
from bake.samples import simple
from bake.ui import console
from bake.utils.exceptions import BakebookError


def init(
    ctx: Context,
    force: force_option = False,
    inline: Annotated[
        bool, typer.Option("--inline", "-i", help="Create bakefile with PEP 723 inline metadata")
    ] = False,
) -> None:
    """Create a new bakefile.py in the current directory."""

    if ctx.obj.bakebook is not None and not force:
        console.error("Bakebook already loaded. Use --force to override.")
        raise typer.Exit(code=1)

    ctx.obj.bakefile_path = resolve_bakefile_path(chdir=ctx.obj.chdir, file_name=ctx.obj.file_name)

    if ctx.obj.bakefile_path.exists() and not force:
        console.error(f"File already exists at {ctx.obj.bakefile_path}. Use --force to overwrite.")
        raise typer.Exit(code=1)

    write_bakefile(
        bakefile_path=ctx.obj.bakefile_path,
        bakebook_name=ctx.obj.bakebook_name,
        sample_module=simple,
    )
    ctx.obj.get_bakebook(allow_missing=False)
    assert ctx.obj.bakebook is not None

    if inline:
        try:
            add_inline_metadata(ctx.obj.bakefile_path)
        except BakebookError as e:
            console.error(f"Failed to add PEP 723 metadata: {e}")
            raise typer.Exit(code=1) from None

        console.success(
            f"Successfully created bakefile with PEP 723 metadata at {ctx.obj.bakefile_path}"
        )
        return

    console.success(f"Successfully created bakefile at {ctx.obj.bakefile_path}")
