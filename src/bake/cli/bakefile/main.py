from bake.cli.common.app import (
    BakefileApp,
    add_completion,
    bake_app_callback_with_obj,
    rich_markup_mode,
)
from bake.cli.common.obj import get_bakefile_object

from . import uv
from .add_inline import add_inline
from .export import export
from .find_python import find_python
from .init import init
from .lint import lint


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

    bakefile_app.callback(invoke_without_command=True)(bake_app_callback_with_obj(obj=bakefile_obj))
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
