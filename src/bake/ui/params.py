from typing import Annotated

import typer

verbose_bool = Annotated[bool, typer.Option("-v", "--verbose", help="Run with verbose output")]
