import typer

from bakefile.cli.bake.resolve_bakebook import resolve_bakebook
from bakefile.cli.utils.version import version_callback

app = typer.Typer(add_completion=False)


@app.command()
def main(
    chdir: str = typer.Option(None, "-C", "--chdir", help="Change directory before running"),
    file_name: str = typer.Option("bakefile.py", "--file-name", "-f", help="Path to bakefile.py"),
    bakebook_name: str = typer.Option(
        "bakebook", "--book-name", "-b", help="Name of bakebook object to retrieve"
    ),
    version: bool = typer.Option(  # noqa: ARG001
        False,
        "--version",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    bakebook = resolve_bakebook(file_name=file_name, bakebook_name=bakebook_name, chdir=chdir)
    typer.echo(bakebook)
