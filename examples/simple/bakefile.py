import typer

bakebook = typer.Typer()


@bakebook.command(name="hello")
def hello(name: str = typer.Option("world", help="Name to greet")) -> None:
    typer.echo(f"Hello {name}!")


@bakebook.command()
def build(
    prod: bool = typer.Option(False, "--prod", help="Production build"),
) -> None:
    typer.echo(f"Building{' (prod)' if prod else ''}...")
