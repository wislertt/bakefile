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
from bake.bakebook.utils import parse_bake_log
from bake.manage.find_python import is_standalone_bakefile
from bake.ui import console
from bake.utils.constants import (
    DEFAULT_BAKE_LOG,
    DEFAULT_BAKE_LOG_PRETTY,
    DEFAULT_BAKE_LOG_VERBOSITY,
    DEFAULT_BAKEBOOK_NAME,
    DEFAULT_CHDIR,
    DEFAULT_DRY_RUN,
    DEFAULT_FILE_NAME,
    DEFAULT_IS_CHAIN_COMMAND,
    GET_BAKEFILE_OBJECT,
    get_default_bake_log,
)
from bake.utils.exceptions import BakebookError, BakefileNotFoundError
from bake.utils.settings import _LOG_LEVELS_TO_VERBOSITY, bake_settings

from .exception_handler import typer_exception_handler
from .params import (
    BakebookNameOption,
    BakeLogOption,
    BakeLogPrettyOption,
    ChdirOption,
    DryRunOption,
    FileNameOption,
    IsChainCommandsOption,
    RemainingArgsArgument,
    VerbosityOption,
    validate_file_name,
)
from .reinvocation import CliModule, _reinvoke_with_detected_python

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
    bake_log_verbosity: int = DEFAULT_BAKE_LOG_VERBOSITY
    dry_run: bool = DEFAULT_DRY_RUN
    bake_log: str = DEFAULT_BAKE_LOG
    bake_log_pretty: bool = DEFAULT_BAKE_LOG_PRETTY
    remaining_args: list[str] | None = None
    is_chain_commands: bool = DEFAULT_IS_CHAIN_COMMAND

    def __post_init__(self):
        validate_file_name(self.file_name)

    @property
    def is_standalone_bakefile(self) -> bool:
        if self.bakefile_path is None:
            return False
        return is_standalone_bakefile(self.bakefile_path)

    def resolve_bakefile_path(self) -> Path | None:
        if self.bakefile_path is not None:
            return self.bakefile_path

        with contextlib.suppress(BakefileNotFoundError):
            self.bakefile_path = resolve_bakefile_path(chdir=self.chdir, file_name=self.file_name)

        return self.bakefile_path

    def get_bakebook(self, allow_missing: bool, reinvoke_cli_module: CliModule | None = None):
        if self.bakebook is not None:
            return

        if reinvoke_cli_module is not None:
            # Check re-invocation with resolved bakefile path
            # If re-invocation happens, process is replaced and we don't return
            _reinvoke_with_detected_python(self.bakefile_path, cli_module=reinvoke_cli_module)
            # If returned above, we're in the correct Python

        try:
            if self.bakefile_path is None:
                self.bakefile_path = resolve_bakefile_path(
                    chdir=self.chdir, file_name=self.file_name
                )
            self.bakebook = get_bakebook_from_target_dir_path(
                target_dir_path=self.bakefile_path, bakebook_name=self.bakebook_name
            )
            self.setup_logging()
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
        bake_settings._bake_logging_setup = False
        if self.bakebook is not None:
            bake_log = self.bakebook.bake_log
            bake_log_pretty = self.bakebook.bake_log_pretty
        else:
            bake_log = self.bake_log
            bake_log_pretty = self.bake_log_pretty

        bake_settings.setup_bake_logging(
            bake_log=bake_log,
            verbosity=self.bake_log_verbosity,
            bake_log_pretty=bake_log_pretty,
        )


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
    chdir: ChdirOption = DEFAULT_CHDIR,
    file_name: FileNameOption = DEFAULT_FILE_NAME,
    bakebook_name: BakebookNameOption = DEFAULT_BAKEBOOK_NAME,
    is_chain_commands: IsChainCommandsOption = DEFAULT_IS_CHAIN_COMMAND,
    remaining_args: RemainingArgsArgument = None,
    bake_log_verbosity: VerbosityOption = None,
    dry_run: DryRunOption = DEFAULT_DRY_RUN,
    bake_log: BakeLogOption = None,
    bake_log_pretty: BakeLogPrettyOption = DEFAULT_BAKE_LOG_PRETTY,
) -> BakefileObject:
    _ = ctx

    effective_bake_log = bake_log if bake_log is not None else get_default_bake_log(file_name)

    if bake_log_verbosity is not None:
        effective_bake_log_verbosity = bake_log_verbosity
    elif bake_log is not None:
        effective_bake_log_verbosity = _LOG_LEVELS_TO_VERBOSITY[
            int(min(parse_bake_log(bake_log).values()))
        ]
    else:
        effective_bake_log_verbosity = DEFAULT_BAKE_LOG_VERBOSITY

    return BakefileObject(
        chdir=chdir,
        file_name=file_name,
        bakebook_name=bakebook_name,
        bake_log_verbosity=effective_bake_log_verbosity,
        dry_run=dry_run,
        bake_log=effective_bake_log,
        bake_log_pretty=bake_log_pretty,
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
