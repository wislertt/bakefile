from collections.abc import Callable

from bake.cli.common.app import (
    BakefileApp,
    add_completion,
    rich_markup_mode,
    show_help_if_no_command,
)
from bake.cli.common.context import Context
from bake.cli.common.obj import BakefileObject, get_bakefile_object
from bake.cli.common.params import (
    bakebook_name_option,
    chdir_option,
    dry_run_option,
    file_name_option,
    verbosity_option,
    version_option,
)
from bake.utils.constants import (
    DEFAULT_BAKEBOOK_NAME,
    DEFAULT_CHDIR,
    DEFAULT_FILE_NAME,
)

from . import uv
from .add_inline import add_inline
from .export import export
from .find_python import find_python
from .init import init
from .lint import lint


def bakefile_app_callback_with_obj(obj: BakefileObject) -> Callable[..., None]:
    def bakefile_app_callback(
        ctx: Context,
        _chdir: chdir_option = DEFAULT_CHDIR,
        _file_name: file_name_option = DEFAULT_FILE_NAME,
        _bakebook_name: bakebook_name_option = DEFAULT_BAKEBOOK_NAME,
        _version: version_option = False,
        _verbosity: verbosity_option = 0,
        _dry_run: dry_run_option = False,
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

    uv_commands_context_settings = {
        "allow_extra_args": True,
        "ignore_unknown_options": True,
    }

    callback = bakefile_app_callback_with_obj(obj=bakefile_obj)
    bakefile_app.callback(invoke_without_command=True)(callback)
    bakefile_app.command()(init)
    bakefile_app.command()(add_inline)
    bakefile_app.command()(find_python)
    bakefile_app.command()(lint)
    bakefile_app.command()(export)
    bakefile_app.command(context_settings=uv_commands_context_settings)(uv.sync)
    bakefile_app.command(context_settings=uv_commands_context_settings)(uv.lock)
    bakefile_app.command(context_settings=uv_commands_context_settings)(uv.add)
    bakefile_app.command(context_settings=uv_commands_context_settings)(uv.pip)
    bakefile_app.bakefile_object = bakefile_obj
    bakefile_app()
