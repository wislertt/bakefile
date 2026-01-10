import typer

from bake import Bakebook, Context, command
from bake.ui import console


class BaseSpace(Bakebook):
    @command()
    def lint(self, ctx: Context) -> None:
        ctx.run(["bunx", "prettier@latest", "--write", "**/*.{js,jsx,ts,tsx,css,json,yaml,yml,md}"])

    @command()
    def test(self) -> None:
        console.error("No implementation")
        raise typer.Exit(1)
