import contextlib
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import click
import typer
from pydantic import ValidationError
from rich.traceback import Traceback
from typer.core import MarkupMode
from typer.main import get_command_from_info

from bake.bakebook.get import (
    get_bakebook_from_target_dir_path,
    resolve_bakefile_path,
)
from bake.ui import console, setup_logging
from bake.utils.constants import (
    DEFAULT_BAKEBOOK_NAME,
    DEFAULT_CHDIR,
    DEFAULT_FILE_NAME,
    DEFAULT_IS_CHAIN_COMMAND,
    GET_BAKEFILE_OBJECT,
)
from bake.utils.exceptions import BakebookError, BakefileNotFoundError

from .callback import validate_file_name
from .exception_handler import typer_exception_handler
from .params import (
    bakebook_name_option,
    chdir_option,
    dry_run_option,
    file_name_option,
    is_chain_commands_option,
    remaining_args_argument,
    verbosity_option,
)

if TYPE_CHECKING:
    from bake.bakebook.bakebook import Bakebook

logger = logging.Logger(__name__)


@dataclass
class BakefileObject:
    chdir: Path
    file_name: str
    bakebook_name: str
    bakefile_path: Path | None = None
    bakebook: "Bakebook | None" = None
    verbosity: int = 0
    dry_run: bool = False
    remaining_args: list[str] | None = None
    is_chain_commands: bool = False

    def __post_init__(self):
        validate_file_name(self.file_name)

    def resolve_bakefile_path(self) -> Path | None:
        if self.bakefile_path is not None:
            return self.bakefile_path

        with contextlib.suppress(BakefileNotFoundError):
            self.bakefile_path = resolve_bakefile_path(chdir=self.chdir, file_name=self.file_name)

        return self.bakefile_path

    def get_bakebook(self, allow_missing: bool):
        if self.bakebook is not None:
            return

        try:
            if self.bakefile_path is None:
                self.bakefile_path = resolve_bakefile_path(
                    chdir=self.chdir, file_name=self.file_name
                )
            self.bakebook = get_bakebook_from_target_dir_path(
                target_dir_path=self.bakefile_path, bakebook_name=self.bakebook_name
            )
        except BakefileNotFoundError as e:
            if allow_missing:
                return
            console.error(str(e))
            raise SystemExit(1) from e
        except BakebookError as e:
            if allow_missing:
                return
            exc_to_show = e.__cause__ if e.__cause__ else e

            if exc_to_show.__class__ in {ValidationError, BakebookError}:
                console.err.print(
                    f"[bold red]{exc_to_show.__class__.__name__}:[/bold red]", end=" "
                )
                console.err.print(exc_to_show)
                console.err.print(f"Searched in: {self.chdir.resolve()}\n")
            else:
                console.err.print(
                    Traceback.from_exception(
                        type(exc_to_show), exc_to_show, exc_to_show.__traceback__
                    )
                )
            raise SystemExit(1) from e

    def warn_if_no_bakebook(self, color_echo: bool):
        if self.bakebook is None:
            _ = color_echo  # Color handled by console module
            console.warning(f"Bakebook `{self.bakebook_name}` not found in `{self.file_name}`")
            console.echo(f"Searched in: {self.chdir.resolve()}\n")

    def setup_logging(self):
        level_map = {0: logging.WARNING, 1: logging.INFO, 2: logging.DEBUG}
        log_level = level_map.get(self.verbosity, logging.WARNING)
        setup_logging(level_per_module={"": log_level}, is_pretty_log=True)


bakefile_obj_app = typer.Typer()


def get_args(args: list[str] | None = None, windows_expand_args: bool = True) -> list[str]:
    if args is None:
        args = sys.argv[1:]

        # Covered in Click tests
        if os.name == "nt" and windows_expand_args:  # pragma: no cover
            args = click.utils._expand_args(args)
    else:
        args = list(args)

    return args


def bakefile_obj_app_args(
    args: list[str] | None = None,
    windows_expand_args: bool = True,
) -> list[str]:
    # source from https://github.com/fastapi/typer/blob/b7f39eaad60141988f5d9a58df72c44d6128cd53/typer/core.py#L175-L185

    args = get_args(args=args, windows_expand_args=windows_expand_args)

    prohibited_non_bakefile_obj_app_args: list[str] = ["--help", "--version"]

    args = [arg for arg in args if arg not in prohibited_non_bakefile_obj_app_args]
    return args


def is_bakebook_optional(remaining_args: list[str] | None) -> bool:
    args = get_args()

    some_args: list[str] = ["--help", "--version"]
    is_some_args = len([arg for arg in args if arg in some_args]) > 0
    return is_some_args or remaining_args is None or remaining_args == []


@bakefile_obj_app.command(
    name=GET_BAKEFILE_OBJECT,
    hidden=True,
    context_settings={
        "allow_extra_args": True,
        "allow_interspersed_args": False,
        "ignore_unknown_options": True,
    },
)
def _get_bakefile_object(
    ctx: typer.Context,
    chdir: chdir_option = DEFAULT_CHDIR,
    file_name: file_name_option = DEFAULT_FILE_NAME,
    bakebook_name: bakebook_name_option = DEFAULT_BAKEBOOK_NAME,
    is_chain_commands: is_chain_commands_option = DEFAULT_IS_CHAIN_COMMAND,
    remaining_args: remaining_args_argument = None,
    verbosity: verbosity_option = 0,
    dry_run: dry_run_option = False,
):
    _ = ctx
    return BakefileObject(
        chdir=chdir,
        file_name=file_name,
        bakebook_name=bakebook_name,
        verbosity=verbosity,
        dry_run=dry_run,
        remaining_args=remaining_args,
        is_chain_commands=is_chain_commands,
    )


def get_bakefile_object(rich_markup_mode: MarkupMode) -> BakefileObject:
    with typer_exception_handler(standalone_mode=True, rich_markup_mode=rich_markup_mode):
        args = bakefile_obj_app_args()

        for registered_command in bakefile_obj_app.registered_commands:
            if registered_command.name != GET_BAKEFILE_OBJECT:
                continue

            command = get_command_from_info(
                registered_command,
                pretty_exceptions_short=bakefile_obj_app.pretty_exceptions_short,
                rich_markup_mode=bakefile_obj_app.rich_markup_mode,
            )

            with command.make_context(info_name=GET_BAKEFILE_OBJECT, args=args) as ctx:
                bakefile_obj = command.invoke(ctx)
                if not isinstance(bakefile_obj, BakefileObject):
                    msg = (
                        f"Expected `bakefile_obj` to be an instance of "
                        f"{BakefileObject.__name__}, got {type(bakefile_obj).__name__}"
                    )
                    raise TypeError(msg)
                return bakefile_obj

    raise RuntimeError(
        f"Failed to find the `{GET_BAKEFILE_OBJECT}` command in registered commands. "
        f"This should never happen - please report this bug."
    )
