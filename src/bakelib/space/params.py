from typing import Annotated

import typer

PublishTokenOption = Annotated[str | None, typer.Option(help="Publish token")]
PublishVersionOption = Annotated[str | None, typer.Option(help="Version to publish")]

DeployVersionOption = Annotated[str | None, typer.Option(help="Version to deploy")]
