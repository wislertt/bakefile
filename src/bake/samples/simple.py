from bake import Bakebook, console

__bakebook__ = Bakebook()


@__bakebook__.command()
def hello(name: str = "world"):
    console.echo(f"Hello {name}!")
