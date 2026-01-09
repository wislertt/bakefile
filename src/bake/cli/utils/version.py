from importlib.metadata import PackageNotFoundError, version

import typer

from bake.ui import console


def _get_version() -> str:
    try:
        return version("bakefile")
    except PackageNotFoundError:
        return "0.0.0"


def version_callback(value: bool) -> None:
    if value:
        console.out.print(_get_version(), style=None, highlight=False)
        raise typer.Exit()
