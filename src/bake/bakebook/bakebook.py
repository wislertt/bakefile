import types
from collections.abc import Callable
from typing import Any, cast

import typer
from pydantic import PrivateAttr
from pydantic_settings import BaseSettings, SettingsConfigDict
from typer.core import TyperCommand
from typer.models import CommandFunctionType, Default

from bake.utils.constants import BAKE_COMMAND_KWARGS


class Bakebook(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    _app: typer.Typer = PrivateAttr(default_factory=typer.Typer)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._register_marked_methods()

    def _register_marked_methods(self) -> None:
        for name in set(dir(self)) - set(dir(BaseSettings())):
            if name.startswith("_"):
                continue

            attr = getattr(self, name)

            if hasattr(attr, BAKE_COMMAND_KWARGS):
                bound_method = getattr(self, name)
                attr = cast(types.MethodType, attr)
                cmd_kwargs = object.__getattribute__(attr.__func__, BAKE_COMMAND_KWARGS)
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
