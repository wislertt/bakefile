import typer

from bakefile.cli.utils.version import version_callback

app = typer.Typer(add_completion=True)


@app.command()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    _ = version
    typer.echo("hello world")
