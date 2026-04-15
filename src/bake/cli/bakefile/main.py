from collections.abc import Callable

from bake.cli.common.app import (
    BakefileApp,
    add_completion,
    call_app_with_chdir,
    rich_markup_mode,
    show_help_if_no_command,
)
from bake.cli.common.context import Context
from bake.cli.common.obj import BakefileObject, get_bakefile_object
from bake.cli.common.params import (
    BakebookNameOption,
    BakeLogOption,
    BakeLogPrettyOption,
    ChdirOption,
    DryRunOption,
    FileNameOption,
    VerbosityOption,
    VersionOption,
)
from bake.utils.constants import (
    DEFAULT_BAKE_LOG,
    DEFAULT_BAKE_LOG_PRETTY,
    DEFAULT_BAKE_LOG_VERBOSITY,
    DEFAULT_BAKEBOOK_NAME,
    DEFAULT_CHDIR,
    DEFAULT_DRY_RUN,
    DEFAULT_FILE_NAME,
)

from . import uv
from .add_inline import add_inline
from .env import env
from .export import export
from .find_python import find_python
from .init import init
from .lint import lint
from .run import run


def bakefile_app_callback_with_obj(obj: BakefileObject) -> Callable[..., None]:
    def bakefile_app_callback(
        ctx: Context,
        _chdir: ChdirOption = DEFAULT_CHDIR,
        _file_name: FileNameOption = DEFAULT_FILE_NAME,
        _bakebook_name: BakebookNameOption = DEFAULT_BAKEBOOK_NAME,
        _version: VersionOption = False,
        _bake_log: BakeLogOption = DEFAULT_BAKE_LOG,
        _bake_log_pretty: BakeLogPrettyOption = DEFAULT_BAKE_LOG_PRETTY,
        _verbosity: VerbosityOption = DEFAULT_BAKE_LOG_VERBOSITY,
        _dry_run: DryRunOption = DEFAULT_DRY_RUN,
    ):
        ctx.obj = obj
        show_help_if_no_command(ctx)

    return bakefile_app_callback


def main():
    bakefile_obj = get_bakefile_object(rich_markup_mode=rich_markup_mode)
    bakefile_obj.setup_logging()
    bakefile_obj.resolve_bakefile_path()

    bakefile_app = BakefileApp(
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
    bakefile_app.command()(lint)
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
