import logging
import types
import warnings
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar

import click
import typer
from pydantic import PrivateAttr
from pydantic.warnings import PydanticDeprecationWarning
from pydantic_settings import BaseSettings, SettingsConfigDict
from typer.core import TyperCommand, TyperGroup
from typer.main import get_command_name
from typer.models import CommandFunctionType, Default

from bake.cli.common.context import BakeCommand, Context
from bake.utils.constants import BAKE_COMMAND_KWARGS
from bake.utils.exceptions import CommandConflictError, ContextNotAvailableError

logger = logging.getLogger(__name__)


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


@dataclass
class CommandGroup:
    """Holds a command group's Typer app."""

    app: typer.Typer

    @property
    def registered_commands(self) -> set[str]:
        return _get_registered_command_names(self.app)


bakebook_model_config_type = ClassVar[SettingsConfigDict]


class Bakebook(BaseSettings):
    model_config: bakebook_model_config_type = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
    _app: typer.Typer = PrivateAttr(default_factory=typer.Typer)
    _command_groups: dict[str, CommandGroup] = PrivateAttr(default_factory=dict)
    exclude_command_methods: ClassVar[list[str]] = []

    @property
    def _registered_commands(self) -> set[str]:
        return _get_registered_command_names(self._app)

    @property
    def ctx(self) -> Context:

        ctx = click.get_current_context(silent=True)
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

    def _get_command_kwargs(self, method: types.MethodType) -> CommandKwargs | None:
        func = method.__func__

        if hasattr(func, BAKE_COMMAND_KWARGS):
            return object.__getattribute__(func, BAKE_COMMAND_KWARGS)

        method_name = method.__name__
        for base in self.__class__.__mro__[1:]:
            if not hasattr(base, method_name):
                continue
            parent_func = getattr(base, method_name)
            if hasattr(parent_func, BAKE_COMMAND_KWARGS):
                return object.__getattribute__(parent_func, BAKE_COMMAND_KWARGS)

        return None

    def _get_bound_method(self, name: str) -> types.MethodType | None:
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    category=PydanticDeprecationWarning,
                    message=".*is deprecated.*",
                )
                bound_method = getattr(self, name)
                if isinstance(bound_method, types.MethodType):
                    return bound_method
        except Exception:
            pass
        return None

    def _register_marked_methods(self) -> None:
        excluded = set(self.__class__.exclude_command_methods)
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

    def _register_command(self, method: types.MethodType, cmd_kwargs: CommandKwargs) -> None:
        cmd_name = cmd_kwargs.name or get_command_name(method.__name__)

        if cmd_kwargs.group_name:
            self._register_grouped_command(method=method, cmd_kwargs=cmd_kwargs, cmd_name=cmd_name)
        else:
            self._register_app_command(method=method, cmd_kwargs=cmd_kwargs, cmd_name=cmd_name)

    def _register_grouped_command(
        self, method: types.MethodType, cmd_kwargs: CommandKwargs, cmd_name: str
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
        self, method: types.MethodType, cmd_kwargs: CommandKwargs, cmd_name: str
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
