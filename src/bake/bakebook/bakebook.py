import types
from collections.abc import Callable
from typing import Any

import typer
from pydantic import PrivateAttr
from pydantic_settings import BaseSettings, SettingsConfigDict
from typer.core import TyperCommand
from typer.models import CommandFunctionType, Default

from bake.cli.common.context import BakeCommand
from bake.utils.constants import BAKE_COMMAND_KWARGS


class Bakebook(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    _app: typer.Typer = PrivateAttr(default_factory=typer.Typer)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._register_marked_methods()

    def _get_command_kwargs(self, method: types.MethodType) -> dict[str, Any] | None:
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

    def _register_marked_methods(self) -> None:
        base_names = set(dir(BaseSettings()))
        method_names = [
            name for name in dir(self) if not name.startswith("_") and name not in base_names
        ]
        for name in method_names:
            bound_method = getattr(self, name)
            if not isinstance(bound_method, types.MethodType):
                continue

            cmd_kwargs = self._get_command_kwargs(bound_method)
            if cmd_kwargs:
                self._app.command(**cmd_kwargs)(bound_method)

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
