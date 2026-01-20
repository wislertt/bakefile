from bake import console
from bakelib import PythonSpace

bakebook = PythonSpace()


@bakebook.command()
def hello(name: str = "world"):
    console.echo(f"Hello {name}!")
