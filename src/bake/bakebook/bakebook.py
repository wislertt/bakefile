import logging
import types
import warnings
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Annotated, Any, ClassVar

import typer
from pydantic import Field, PrivateAttr, field_validator
from pydantic.warnings import PydanticDeprecationWarning
from pydantic_settings import BaseSettings, SettingsConfigDict
from typer._click.globals import get_current_context
from typer.core import TyperCommand, TyperGroup
from typer.main import get_command_name
from typer.models import CommandFunctionType, Default

from bake.cli.common.context import BakeCommand, Context
from bake.utils.constants import (
    BAKE_COMMAND_KWARGS,
    DEFAULT_BAKE_LOG,
    DEFAULT_BAKE_LOG_PRETTY,
    DEFAULT_BAKE_LOG_VERBOSITY,
)
from bake.utils.exceptions import CommandConflictError, ContextNotAvailableError
from bake.utils.settings import bake_settings

logger = logging.getLogger(__name__)

# A function or method that can be used as a command
CommandFunction = types.FunctionType | types.MethodType

# Type alias for bake_log_verbosity field.
# 0 = silent, 1 = WARNING+, 2 = INFO+, 3 = DEBUG+ (global log-level floor).
BakeLogVerbosityField = Annotated[int, Field(ge=0, le=3)]


@dataclass
class CommandKwargs:
    """Type-safe kwargs for command registration."""

    name: str | None = None
    group_name: str | None = None
    cls: type[TyperCommand] | None = None
    context_settings: dict[Any, Any] | None = None
    help: str | None = None
    epilog: str | None = None
    short_help: str | None = None
    options_metavar: str | None = None
    add_help_option: bool = True
    no_args_is_help: bool = False
    hidden: bool = False
    deprecated: bool = False
    rich_help_panel: str | None = None  # Simplified from Default(None)

    def to_typer_kwargs(self) -> dict[str, Any]:
        """Convert to dict for typer, excluding custom fields and None values."""
        result: dict[str, Any] = {}
        for key, value in vars(self).items():
            if value is None or key == "group_name":
                continue
            result[key] = value
        return result


@dataclass
class GroupKwargs:
    """Type-safe kwargs for command group registration (add_typer)."""

    cls: type[TyperGroup] | None = None
    invoke_without_command: bool = False
    no_args_is_help: bool = False
    subcommand_metavar: str | None = None
    chain: bool = False
    result_callback: Callable[..., Any] | None = None
    context_settings: dict[Any, Any] | None = None
    callback: Callable[..., Any] | None = None
    help: str | None = None
    epilog: str | None = None
    short_help: str | None = None
    options_metavar: str | None = None
    add_help_option: bool = True
    hidden: bool = False
    deprecated: bool = False
    rich_help_panel: str | None = None

    def to_typer_kwargs(self) -> dict[str, Any]:
        """Convert to dict for add_typer, excluding None values."""
        return {k: v for k, v in vars(self).items() if v is not None}


def _get_registered_command_names(app: typer.Typer) -> set[str]:
    """Extract registered command names from a Typer app."""
    result = set()
    for cmd in app.registered_commands:
        if cmd.name:
            result.add(cmd.name)
        elif cmd.callback:
            name = getattr(cmd.callback, "__name__", None)
            if name:
                result.add(get_command_name(name))
    return result


def _try_get_command_metadata(obj: Any) -> CommandKwargs | None:
    """Safely get command metadata from an object."""
    if hasattr(obj, BAKE_COMMAND_KWARGS):
        return object.__getattribute__(obj, BAKE_COMMAND_KWARGS)
    return None


def _get_command_kwargs_from_class(base: type, method_name: str) -> CommandKwargs | None:
    """Get command kwargs from a specific class in the MRO."""
    # Not in __dict__ - try getattr
    if method_name not in base.__dict__:
        return _try_get_command_metadata(getattr(base, method_name))

    # In __dict__ - handle descriptor (staticmethod/classmethod)
    func_or_descriptor = base.__dict__[method_name]

    # Check descriptor first (@command then @staticmethod/@classmethod)
    if command_kwargs := _try_get_command_metadata(func_or_descriptor):
        return command_kwargs

    # For staticmethod/classmethod, also check __func__ (reverse decorator order)
    if isinstance(func_or_descriptor, (staticmethod, classmethod)) and (
        command_kwargs := _try_get_command_metadata(func_or_descriptor.__func__)
    ):
        return command_kwargs

    # Regular function/method - check if it has metadata
    return _try_get_command_metadata(func_or_descriptor)


@dataclass
class CommandGroup:
    """Holds a command group's Typer app."""

    app: typer.Typer

    @property
    def registered_commands(self) -> set[str]:
        return _get_registered_command_names(self.app)


class BakebookMixin(BaseSettings):
    """Base class for composable Bakebook mixins.

    Use instead of inheriting from Bakebook when creating mixin classes.
    Multiple BakebookMixin subclasses can be composed with a single Bakebook
    subclass without MRO conflicts.

    Recommended usage: fields only — no methods. This keeps mixins simple
    and avoids the need for typed access to base class attributes.
    Use ``Bakebook`` subclasses for methods and ``@command()`` definitions.
    """

    def __init__(self, **kwargs: Any) -> None:
        if not isinstance(self, Bakebook):
            raise TypeError("BakebookMixin can only be used with Bakebook subclasses")
        super().__init__(**kwargs)


class Bakebook(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Logging lifecycle:
    # - CLI initial setup: before bakebook object is loaded (CLI args/env vars)
    # - CLI post-bakebook setup: after bakebook object is loaded (bakebook fields)
    # - User explicit setup: setup_logging() called directly by user (non-CLI entry)

    bake_log: str = (
        # Logging config (level per module).
        # Affects CLI post-bakebook setup and user explicit setup.
        # Can also be set via CLI `--bake-log` or env `BAKE_LOG` (CLI initial setup).
        DEFAULT_BAKE_LOG
    )
    bake_log_verbosity: BakeLogVerbosityField = (
        # Global log-level floor: 0 = silent, 1 = WARNING+, 2 = INFO+, 3 = DEBUG+.
        # Only affects non-CLI entry (e.g. `uv run test.py`).
        # CLI entry is fully controlled by `-v`/`-vv`/`-vvv` flags (CLI initial setup).
        DEFAULT_BAKE_LOG_VERBOSITY
    )
    bake_log_pretty: bool = (
        # Use pretty log format (vs JSON). Affects CLI post-bakebook setup and user explicit setup.
        # Can also be set via CLI `--log-pretty`/`--no-log-pretty` or env `BAKE_LOG_PRETTY`
        # (CLI initial setup).
        DEFAULT_BAKE_LOG_PRETTY
    )

    _app: typer.Typer = PrivateAttr(default_factory=typer.Typer)
    _command_groups: dict[str, CommandGroup] = PrivateAttr(default_factory=dict)
    __exclude_command_methods__: ClassVar[list[str]] = (
        # Method names to exclude from command registration.
        # Subclasses override this to prevent inherited methods from being
        # registered as commands. Uses method names, not command names.
        []
    )

    @field_validator("bake_log")
    @classmethod
    def _validate_bake_log(cls, v: str) -> str:
        from bake.bakebook.utils import parse_bake_log, serialize_bake_log

        return serialize_bake_log(parse_bake_log(v))

    @property
    def _registered_commands(self) -> set[str]:
        return _get_registered_command_names(self._app)

    @property
    def ctx(self) -> Context:

        ctx = get_current_context(silent=True)
        if ctx is None:
            raise ContextNotAvailableError(
                "Command context not available - "
                "this method must be called from within a bake command"
            )
        if not isinstance(ctx, Context):
            raise ContextNotAvailableError(f"Expected {Context}, got {type(ctx)}")
        return ctx

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._register_marked_methods()

    def _get_command_kwargs(self, method: CommandFunction) -> CommandKwargs | None:
        """Get command kwargs from a method, static method, or class method."""
        # Get the underlying function
        func = method.__func__ if isinstance(method, types.MethodType) else method

        # Direct check on the function itself
        if command_kwargs := _try_get_command_metadata(func):
            return command_kwargs

        # Search through MRO for inherited commands
        method_name = method.__name__
        for base in self.__class__.__mro__:
            if hasattr(base, method_name) and (
                command_kwargs := _get_command_kwargs_from_class(base, method_name)
            ):
                return command_kwargs

        return None

    def _get_bound_method(self, name: str) -> CommandFunction | None:
        """Get a bound method, static method, or class method by name."""
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    category=PydanticDeprecationWarning,
                    message=".*is deprecated.*",
                )
                obj = getattr(self, name)
                # Accept regular methods, static methods, and class methods
                if isinstance(obj, (types.MethodType, types.FunctionType)):
                    return obj
        except Exception:
            pass
        return None

    def _register_marked_methods(self) -> None:
        excluded = set(self.__class__.__exclude_command_methods__)
        logger.debug("Excluding %d methods: %s", len(excluded), excluded)

        for name in dir(self):
            if name in excluded:
                continue

            bound_method = self._get_bound_method(name)
            if bound_method is None:
                continue

            cmd_kwargs = self._get_command_kwargs(bound_method)
            if cmd_kwargs:
                self._register_command(bound_method, cmd_kwargs)

    def _register_command(self, method: CommandFunction, cmd_kwargs: CommandKwargs) -> None:
        cmd_name = cmd_kwargs.name or get_command_name(method.__name__)

        if cmd_kwargs.group_name:
            self._register_grouped_command(method=method, cmd_kwargs=cmd_kwargs, cmd_name=cmd_name)
        else:
            self._register_app_command(method=method, cmd_kwargs=cmd_kwargs, cmd_name=cmd_name)

    def _register_grouped_command(
        self, method: CommandFunction, cmd_kwargs: CommandKwargs, cmd_name: str
    ) -> None:
        assert cmd_kwargs.group_name is not None  # Type narrowing
        group = self._get_or_create_group(cmd_kwargs.group_name)
        if cmd_name in group.registered_commands:
            raise CommandConflictError(
                f"Cannot register command '{cmd_name}' in group '{cmd_kwargs.group_name}': "
                f"a command with this name already exists in the group"
            )
        group.app.command(**cmd_kwargs.to_typer_kwargs())(method)

    def _register_app_command(
        self, method: CommandFunction, cmd_kwargs: CommandKwargs, cmd_name: str
    ) -> None:
        if cmd_name in self._command_groups:
            raise CommandConflictError(
                f"Cannot register command '{cmd_name}': "
                f"a command group with this name already exists"
            )
        if cmd_name in self._registered_commands:
            raise CommandConflictError(
                f"Cannot register command '{cmd_name}': a command with this name already exists"
            )
        self._app.command(**cmd_kwargs.to_typer_kwargs())(method)

    def _get_or_create_group(self, name: str) -> CommandGroup:
        """Get existing command group or create with config from get_group_kwargs()."""
        if name not in self._command_groups:
            # Check for conflict with existing command
            if name in self._registered_commands:
                raise CommandConflictError(
                    f"Cannot create command group '{name}': a command with this name already exists"
                )
            group_kwargs = self.get_group_kwargs().get(name, GroupKwargs())

            app = typer.Typer()
            self._app.add_typer(app, name=name, **group_kwargs.to_typer_kwargs())
            self._command_groups[name] = CommandGroup(app=app)
        return self._command_groups[name]

    def get_group_kwargs(self) -> dict[str, GroupKwargs]:
        """Override to configure command groups. Key is group name."""
        return {}

    def get_bake_log_thread_local_context(self) -> dict[str, ContextVar[Any]]:
        """Override to inject ContextVars into bake's logger output."""
        return {}

    def setup_logging(self) -> None:
        bake_settings.setup_bake_logging(
            bake_log=self.bake_log,
            verbosity=self.bake_log_verbosity,
            bake_log_pretty=self.bake_log_pretty,
            thread_local_context=self.get_bake_log_thread_local_context(),
        )

    def command(
        self,
        name: str | None = None,
        *,
        cls: type[TyperCommand] | None = None,
        context_settings: dict[Any, Any] | None = None,
        help: str | None = None,
        epilog: str | None = None,
        short_help: str | None = None,
        options_metavar: str | None = None,
        add_help_option: bool = True,
        no_args_is_help: bool = False,
        hidden: bool = False,
        deprecated: bool = False,
        rich_help_panel: str | None = Default(None),
    ) -> Callable[[CommandFunctionType], CommandFunctionType]:
        if cls is None:
            cls = BakeCommand

        return self._app.command(
            name=name,
            cls=cls,
            context_settings=context_settings,
            help=help,
            epilog=epilog,
            short_help=short_help,
            options_metavar=options_metavar,
            add_help_option=add_help_option,
            no_args_is_help=no_args_is_help,
            hidden=hidden,
            deprecated=deprecated,
            rich_help_panel=rich_help_panel,
        )
