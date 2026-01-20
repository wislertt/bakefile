# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "bakefile>=0.0.0",
# ]
#
# [tool.uv.sources]
# bakefile = { path = "../../", editable = true }
# ///

import logging

import typer

from bake import Bakebook, Context, command, console

logger = logging.getLogger(__name__)


class MyBakebook(Bakebook):
    foo_url: str = "https://example.com"

    @command()
    def foo(self):
        console.echo(f"Doing foo with {self.foo_url}")

    @command()
    def update(self, ctx: Context) -> None:
        ctx.run("bakefile lock --upgrade")
        ctx.run("bakefile sync")


bakebook = MyBakebook()


@bakebook.command(name="hello")
def hello(name: str = typer.Option("world", help="Name to greet")) -> None:
    logger.debug(f"Hello {name}!")
    logger.info(f"Hello {name}!")
    logger.warning(f"Hello {name}!")
    logger.error(f"Hello {name}!")
    console.echo(f"Hello {name}!")
