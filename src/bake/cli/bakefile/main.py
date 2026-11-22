from collections.abc import Callable

import typer

from bake.cli.common.app import (
    AGENT_DOCS_EPILOG,
    BakefileApp,
    add_completion,
    call_app_with_chdir,
    rich_markup_mode,
    show_help_if_no_command,
)
from bake.cli.common.context import Context
from bake.cli.common.obj import BakefileObject, get_args, get_bakefile_object
from bake.cli.common.params import (
    BakebookNameOption,
    BakefileVersionOption,
    BakeLogOption,
    BakeLogPrettyOption,
    ChdirOption,
    DryRunOption,
    FileNameOption,
    GlobalOption,
    VerbosityOption,
)
from bake.ui import console, style
from bake.utils.constants import (
    DEFAULT_BAKE_LOG,
    DEFAULT_BAKE_LOG_PRETTY,
    DEFAULT_BAKE_LOG_VERBOSITY,
    DEFAULT_BAKEBOOK_NAME,
    DEFAULT_CHDIR,
    DEFAULT_DRY_RUN,
    DEFAULT_FILE_NAME,
)
from bake.utils.settings import bake_settings

from . import uv
from .add_inline import add_inline
from .env import env
from .export import export
from .find_python import find_python
from .init import init
from .lint import lint
from .run import run
from .venv import venv
from .which import which


def bakefile_app_callback_with_obj(obj: BakefileObject) -> Callable[..., None]:
    def bakefile_app_callback(
        ctx: Context,
        _chdir: ChdirOption = DEFAULT_CHDIR,
        _file_name: FileNameOption = DEFAULT_FILE_NAME,
        _bakebook_name: BakebookNameOption = DEFAULT_BAKEBOOK_NAME,
        _use_global: GlobalOption = False,
        _version: BakefileVersionOption = False,
        _bake_log: BakeLogOption = DEFAULT_BAKE_LOG,
        _bake_log_pretty: BakeLogPrettyOption = DEFAULT_BAKE_LOG_PRETTY,
        _verbosity: VerbosityOption = DEFAULT_BAKE_LOG_VERBOSITY,
        _dry_run: DryRunOption = DEFAULT_DRY_RUN,
    ):
        ctx.obj = obj
        show_help_if_no_command(ctx)
        _exit_if_global_bakefile_missing(obj, ctx.invoked_subcommand)
        _print_using_bakefile(obj, ctx.invoked_subcommand)

    return bakefile_app_callback


def _acts_on_bakefile(subcommand: str | None) -> bool:
    return subcommand not in (None, init.__name__) and "--help" not in get_args()


def _exit_if_global_bakefile_missing(obj: BakefileObject, subcommand: str | None) -> None:
    if not _acts_on_bakefile(subcommand):
        return
    if obj.resolution is None or obj.resolution.resolved_by != "global" or obj.resolution.found:
        return
    console.error(obj.resolution.not_found_message())
    raise typer.Exit(code=1)


def _print_using_bakefile(obj: BakefileObject, subcommand: str | None) -> None:
    if not _acts_on_bakefile(subcommand):
        return
    # The parent process already printed it before re-invoking
    if bake_settings.bake_reinvoked:
        return
    if obj.resolution is None or not obj.resolution.found:
        return
    console.echo(
        f"Using: {obj.resolution.path}",
        stderr=True,
        soft_wrap=True,
        markup=False,
        highlight=False,
        style="dim",
    )


def main():
    bakefile_obj = get_bakefile_object(rich_markup_mode=rich_markup_mode)
    bakefile_obj.setup_logging()
    bakefile_obj.resolve_bakefile_path()

    bakefile_app = BakefileApp(
        help=f"Manage bakefile.py. Use {style.code('bake')} to run tasks.",
        epilog=AGENT_DOCS_EPILOG,
        add_completion=add_completion,
        rich_markup_mode=rich_markup_mode,
    )

    pass_through_context_settings = {
        "allow_extra_args": True,
        "ignore_unknown_options": True,
    }

    prog_name = "bakefile"

    callback = bakefile_app_callback_with_obj(obj=bakefile_obj)
    bakefile_app.callback(invoke_without_command=True)(callback)
    bakefile_app.command()(init)
    bakefile_app.command()(add_inline)
    bakefile_app.command()(find_python)
    bakefile_app.command()(which)
    bakefile_app.command()(lint)
    bakefile_app.command()(venv)
    bakefile_app.command()(export)
    bakefile_app.command(context_settings=pass_through_context_settings)(env)
    bakefile_app.command(context_settings=pass_through_context_settings)(uv.sync)
    bakefile_app.command(context_settings=pass_through_context_settings)(uv.lock)
    bakefile_app.command(context_settings=pass_through_context_settings)(uv.add)
    bakefile_app.command(context_settings=pass_through_context_settings)(uv.pip)
    bakefile_app.command(context_settings=pass_through_context_settings, add_help_option=False)(run)
    bakefile_app.bakefile_object = bakefile_obj
    call_app_with_chdir(
        app=bakefile_app, bakefile_path=bakefile_obj.bakefile_path, prog_name=prog_name
    )
