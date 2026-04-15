from typing import Annotated

import typer

VerboseBoolOption = Annotated[bool, typer.Option("-v", "--verbose", help="Run with verbose output")]
