from typing import Annotated

import typer

# ==========================================================
# Publish Command Parameters
# ==========================================================
publish_token_option = Annotated[str | None, typer.Option(help="Publish token")]
publish_version_option = Annotated[str | None, typer.Option(help="Version to publish")]
