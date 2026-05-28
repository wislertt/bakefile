from typing import Annotated

import typer

from bake.bakebook.bakebook import BakeLogVerbosityField
from bake.ui.params import VerboseBoolOption


def fast_option(help: str = "Skip steps (repeat to skip more)"):
    return typer.Option("--fast", "-f", count=True, help=help)


FastOption = Annotated[int, fast_option()]


def fast_bool_option(help: str = "Skip heavy operations"):
    return typer.Option("--fast", "-f", help=help)


FastBoolOption = Annotated[bool, fast_bool_option()]

__all__ = [
    "BakeLogVerbosityField",
    "FastBoolOption",
    "FastOption",
    "VerboseBoolOption",
    "fast_bool_option",
    "fast_option",
]
