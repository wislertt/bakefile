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


def slow_option(help: str = "Add slow steps (repeat to add more)"):
    return typer.Option("--slow", "-s", count=True, help=help)


SlowOption = Annotated[int, slow_option()]

__all__ = [
    "BakeLogVerbosityField",
    "FastBoolOption",
    "FastOption",
    "SlowOption",
    "VerboseBoolOption",
    "fast_bool_option",
    "fast_option",
    "slow_option",
]
