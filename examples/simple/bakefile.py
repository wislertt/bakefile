# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "bakefile>=0.0.4",
#     "numpy>=2.4.0",
# ]
#
# [tool.uv.sources]
# bakefile = { path = "../../", editable = true }
# ///

import logging

import typer

from bake import Bakebook, command
from bake.cli.common.context import Context
from bake.ui import console

logger = logging.getLogger(__name__)


class MyBakebook(Bakebook):
    database_url: str = "sqlite:///default.db"
    debug: bool = False

    @command()
    def migrate(self):
        console.echo(f"Migrating {self.database_url}")

    @command(name="deploy-something")
    def deploy(self):
        if self.debug:
            console.echo("Debug mode - skipping deployment")
        else:
            console.echo("Deploying...")


bakebook = Bakebook()


@bakebook.command(name="hello")
def hello(name: str = typer.Option("world", help="Name to greet")) -> None:
    logger.debug(f"Hello {name}!")
    logger.info(f"Hello {name}!")
    logger.warning(f"Hello {name}!")
    logger.error(f"Hello {name}!")
    console.echo(f"Hello {name}!")


@bakebook.command()
def build(
    ctx: Context,
    prod: bool = typer.Option(False, "--prod", help="Production build"),
) -> None:
    if ctx.obj.dry_run:
        console.err.print("This is dry run")

    console.success(f"Building{' (prod)' if prod else ''}...")
