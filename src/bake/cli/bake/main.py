import logging
import sys
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path

import typer

from bake.cli.common.app import (
    add_completion,
    call_app_with_chdir,
    rich_markup_mode,
    show_help_if_no_command,
)
from bake.cli.common.context import Context
from bake.cli.common.obj import BakefileObject, get_bakefile_object, is_bakebook_optional
from bake.cli.common.params import (
    BakebookNameOption,
    BakeLogOption,
    BakeLogPrettyOption,
    BakeVersionOption,
    ChdirOption,
    DryRunOption,
    FileNameOption,
    IsChainCommandsOption,
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
    DEFAULT_IS_CHAIN_COMMAND,
)
from bake.utils.settings import bake_settings

logger = logging.getLogger(__name__)


def bake_app_callback_with_obj(obj: BakefileObject) -> Callable[..., None]:
    def bake_app_callback(
        ctx: Context,
        _chdir: ChdirOption = DEFAULT_CHDIR,
        _file_name: FileNameOption = DEFAULT_FILE_NAME,
        _bakebook_name: BakebookNameOption = DEFAULT_BAKEBOOK_NAME,
        _version: BakeVersionOption = False,
        _is_chain_commands: IsChainCommandsOption = DEFAULT_IS_CHAIN_COMMAND,
        _bake_log: BakeLogOption = DEFAULT_BAKE_LOG,
        _bake_log_pretty: BakeLogPrettyOption = DEFAULT_BAKE_LOG_PRETTY,
        _verbosity: VerbosityOption = DEFAULT_BAKE_LOG_VERBOSITY,
        _dry_run: DryRunOption = DEFAULT_DRY_RUN,
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


def _run_chain_commands(
    remaining_args: list[str], prog_name: str, bake_app: typer.Typer, bakefile_path: Path | None
) -> int:
    exit_code = 0
    for cmd in remaining_args:
        try:
            with set_argv([prog_name, cmd]):
                console.cmd(" ".join(sys.argv))
                call_app_with_chdir(app=bake_app, bakefile_path=bakefile_path, prog_name=prog_name)
        except SystemExit as e:
            if e.code is not None and e.code != 0:
                exit_code = e.code if isinstance(e.code, int) else 1
                break
    return exit_code


def main():
    bakefile_obj = get_bakefile_object(rich_markup_mode=rich_markup_mode)
    bakefile_obj.setup_logging()
    bakefile_obj.resolve_bakefile_path()

    bakefile_obj.get_bakebook(
        allow_missing=is_bakebook_optional(remaining_args=bakefile_obj.remaining_args),
        reinvoke_cli_module="bake.cli.bake",
    )

    bakefile_obj.warn_if_no_bakebook(color_echo=bake_settings.should_use_colors())

    bake_app = typer.Typer(
        help=f"Run tasks from bakefile.py. Use {style.code('bakefile')} to manage it.",
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
            remaining_args=bakefile_obj.remaining_args,
            prog_name=prog_name,
            bake_app=bake_app,
            bakefile_path=bakefile_obj.bakefile_path,
        )
        raise SystemExit(exit_code)
    call_app_with_chdir(app=bake_app, bakefile_path=bakefile_obj.bakefile_path, prog_name=prog_name)
