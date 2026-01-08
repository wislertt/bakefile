import typer

from bake.cli.bake.reinvocation import _reinvoke_with_detected_python
from bake.cli.common.app import (
    add_completion,
    bake_app_callback_with_obj,
    rich_markup_mode,
)
from bake.cli.common.obj import get_bakefile_object, is_bakebook_optional
from bake.utils import env


def main():
    bakefile_obj = get_bakefile_object(rich_markup_mode=rich_markup_mode)
    bakefile_obj.setup_logging()
    bakefile_obj.resolve_bakefile_path()

    # Check re-invocation with resolved bakefile path
    # If re-invocation happens, process is replaced and we don't return
    _reinvoke_with_detected_python(bakefile_obj.bakefile_path)
    # If returned above, we're in the correct Python

    bakefile_obj.get_bakebook(
        allow_missing=is_bakebook_optional(remaining_args=bakefile_obj.remaining_args)
    )

    bakefile_obj.warn_if_no_bakebook(color_echo=env.should_use_colors())

    bake_app = typer.Typer(
        add_completion=add_completion,
        rich_markup_mode=rich_markup_mode,
    )

    bake_app.callback(invoke_without_command=True)(bake_app_callback_with_obj(obj=bakefile_obj))

    if bakefile_obj.bakebook is not None:
        bake_app.add_typer(bakefile_obj.bakebook._app)

    bake_app()
