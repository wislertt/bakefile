from bake import command, console
from bakelib import PythonSpace


class MyBakebook(PythonSpace):
    def _get_mise_tools(self) -> set[str]:
        mise_tools = super()._get_mise_tools()
        mise_tools.remove("pipx:bakefile[extras=locked]")
        return mise_tools

    # Override an inherited task: same tests, but stop at the first failure
    def test(self) -> None:
        self._test(tests_paths="tests/", extra_args="-x")

    # A project-specific task on top of the space
    @command(help="Build the package into dist/")
    def build(self) -> None:
        self.ctx.run("uv build")


bakebook = MyBakebook()


@bakebook.command()
def hello(name: str = "world"):
    console.echo(f"Hello {name}!")
