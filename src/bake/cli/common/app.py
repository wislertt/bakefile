from collections.abc import Callable

import typer
from typer.core import MarkupMode

from bake.cli.common.context import Context
from bake.cli.common.params import (
    bakebook_name_option,
    chdir_option,
    dry_run_option,
    file_name_option,
    is_chain_commands_option,
    verbosity_option,
    version_option,
)
from bake.ui import console
from bake.utils.constants import (
    DEFAULT_BAKEBOOK_NAME,
    DEFAULT_CHDIR,
    DEFAULT_FILE_NAME,
    DEFAULT_IS_CHAIN_COMMAND,
)

from .obj import BakefileObject

rich_markup_mode: MarkupMode = "rich" if not console.out.no_color else None
add_completion = True


class BakefileApp(typer.Typer):
    bakefile_object: BakefileObject


def show_help_if_no_command(ctx: Context) -> None:
    if ctx.invoked_subcommand is None:
        console.echo(ctx.get_help())
        raise typer.Exit(1)


def bake_app_callback_with_obj(obj: BakefileObject) -> Callable:
    def bake_app_callback(
        ctx: Context,
        _chdir: chdir_option = DEFAULT_CHDIR,
        _file_name: file_name_option = DEFAULT_FILE_NAME,
        _bakebook_name: bakebook_name_option = DEFAULT_BAKEBOOK_NAME,
        _version: version_option = False,
        _is_chain_commands: is_chain_commands_option = DEFAULT_IS_CHAIN_COMMAND,
        _verbosity: verbosity_option = 0,
        _dry_run: dry_run_option = False,
    ):
        ctx.obj = obj
        show_help_if_no_command(ctx)

    return bake_app_callback
