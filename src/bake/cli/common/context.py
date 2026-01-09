import typer

from .obj import BakefileObject


class Context(typer.Context):
    obj: BakefileObject
