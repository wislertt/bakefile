from bake import console
from bakelib import PythonSpace


class MyBakebook(PythonSpace):
    def _get_mise_tools(self) -> set[str]:
        mise_tools = super()._get_mise_tools()
        mise_tools.remove("pipx:bakefile")
        return mise_tools


bakebook = MyBakebook()


@bakebook.command()
def hello(name: str = "world"):
    console.echo(f"Hello {name}!")
