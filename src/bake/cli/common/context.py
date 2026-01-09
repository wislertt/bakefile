import click
import typer
from typer.core import TyperCommand

from .obj import BakefileObject


class Context(typer.Context):
    obj: BakefileObject


class BakeCommand(TyperCommand):
    context_class: type[click.Context] = Context
