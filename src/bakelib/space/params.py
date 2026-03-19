from typing import Annotated

import typer

# ==========================================================
# Publish Command Parameters
# ==========================================================
PublishTokenOption = Annotated[str | None, typer.Option(help="Publish token")]
PublishVersionOption = Annotated[str | None, typer.Option(help="Version to publish")]

# ==========================================================
# Misc. Command Parameters
# ==========================================================
DeployVersionOption = Annotated[str | None, typer.Option(help="Version to deploy")]
