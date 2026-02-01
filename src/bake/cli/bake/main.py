import sys
from collections.abc import Callable
from contextlib import contextmanager

import typer

from bake.cli.bake.reinvocation import _reinvoke_with_detected_python
from bake.cli.common.app import add_completion, rich_markup_mode, show_help_if_no_command
from bake.cli.common.context import Context
from bake.cli.common.obj import BakefileObject, get_bakefile_object, is_bakebook_optional
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
from bake.utils.settings import bake_settings


def bake_app_callback_with_obj(obj: BakefileObject) -> Callable[..., None]:
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


@contextmanager
def set_argv(argv: list[str]):
    original = sys.argv.copy()
    sys.argv = argv
    try:
        yield
    finally:
        sys.argv = original


def _run_chain_commands(remaining_args: list[str], prog_name: str, bake_app: typer.Typer) -> int:
    exit_code = 0
    for cmd in remaining_args:
        try:
            with set_argv([prog_name, cmd]):
                console.cmd(" ".join(sys.argv))
                bake_app(prog_name=prog_name)
        except SystemExit as e:
            if e.code is not None and e.code != 0:
                exit_code = e.code if isinstance(e.code, int) else 1
                break
    return exit_code


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

    bakefile_obj.warn_if_no_bakebook(color_echo=bake_settings.should_use_colors())

    bake_app = typer.Typer(
        add_completion=add_completion,
        rich_markup_mode=rich_markup_mode,
    )

    callback = bake_app_callback_with_obj(obj=bakefile_obj)
    bake_app.callback(invoke_without_command=True)(callback)

    prog_name = "bake"

    if bakefile_obj.bakebook is not None:
        bake_app.add_typer(bakefile_obj.bakebook._app)

    if bakefile_obj.is_chain_commands and bakefile_obj.remaining_args:
        exit_code = _run_chain_commands(
            remaining_args=bakefile_obj.remaining_args, prog_name=prog_name, bake_app=bake_app
        )
        raise SystemExit(exit_code)
    bake_app(prog_name=prog_name)
