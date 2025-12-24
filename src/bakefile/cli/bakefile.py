import typer

from bakefile.cli.utils.version import version_callback

app = typer.Typer(add_completion=False)


@app.command()
def main(
    version: bool = typer.Option(  # noqa: ARG001
        False,
        "--version",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    typer.echo("hello world")
