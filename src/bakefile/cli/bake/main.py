import typer

from bakefile.cli.bake.resolve_bakebook import resolve_bakebook

app = typer.Typer()


@app.command()
def main(
    chdir: str = typer.Option(None, "-C", "--chdir", help="Change directory before running"),
    file_name: str = typer.Option("bakefile.py", "--file-name", "-f", help="Path to bakefile.py"),
    bakebook_name: str = typer.Option(
        "bakebook", "--book-name", "-b", help="Name of bakebook object to retrieve"
    ),
) -> None:
    bakebook = resolve_bakebook(file_name=file_name, bakebook_name=bakebook_name, chdir=chdir)
    typer.echo(bakebook)
