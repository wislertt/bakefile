from typing import Annotated

import typer

PublishTokenOption = Annotated[str | None, typer.Option(help="Publish token")]
PublishVersionOption = Annotated[str | None, typer.Option(help="Version to publish")]

DeployVersionOption = Annotated[str | None, typer.Option(help="Version to deploy")]


def fast_option(help: str = "Skip steps (repeat to skip more)"):
    return typer.Option("--fast", "-f", count=True, help=help)


FastOption = Annotated[int, fast_option()]


def fast_bool_option(help: str = "Skip heavy operations"):
    return typer.Option("--fast", "-f", help=help)


FastBoolOption = Annotated[bool, fast_bool_option()]
