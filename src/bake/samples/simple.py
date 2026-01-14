from bake.bakebook.bakebook import Bakebook
from bake.ui import console

__bakebook__ = Bakebook()


@__bakebook__.command()
def hello(name: str = "world"):
    console.echo(f"Hello {name}!")
