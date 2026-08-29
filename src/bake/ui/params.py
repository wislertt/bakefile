from typing import Annotated

import typer

VerboseBoolOption = Annotated[bool, typer.Option("-v", "--verbose", help="Run with verbose output")]

DurationsOption = Annotated[
    int | None,
    typer.Option("-d", "--durations", help="Show N slowest tests (0 for all)"),
]
