from typing import Annotated

import typer

VerboseBool = Annotated[bool, typer.Option("-v", "--verbose", help="Run with verbose output")]
