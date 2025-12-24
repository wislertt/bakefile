import typer

from bakefile import __version__


def version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()
