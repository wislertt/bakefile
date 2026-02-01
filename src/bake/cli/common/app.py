import typer
from typer.core import MarkupMode

from bake.cli.common.context import Context
from bake.ui import console

from .obj import BakefileObject

rich_markup_mode: MarkupMode = "rich" if not console.out.no_color else None
add_completion = True


class BakefileApp(typer.Typer):
    bakefile_object: BakefileObject


def show_help_if_no_command(ctx: Context) -> None:
    if ctx.invoked_subcommand is None:
        console.echo(ctx.get_help())
        raise typer.Exit(1)
