import os
import sys
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import typer

from bake._typer_compat import MarkupMode
from bake.cli.common.context import Context
from bake.ui import console, style

from .obj import BakefileObject

rich_markup_mode: MarkupMode = "rich" if not console.out.no_color else None
add_completion = True

DOCS_URL = "https://bakefile.wisl.dev"
_INSTALL_SKILL_CMD = f"npx skills add {DOCS_URL}"
AGENT_DOCS_EPILOG = f"""Docs: {DOCS_URL}
Full docs in one file (for AI agents): {DOCS_URL}/llms-full.txt
Docs index: {DOCS_URL}/llms.txt
Agent skill: {DOCS_URL}/skill.md
Install agent skill: {style.code(_INSTALL_SKILL_CMD)}
Docs search via MCP: {DOCS_URL}/mcp"""


class BakefileApp(typer.Typer):
    bakefile_object: BakefileObject


if sys.version_info >= (3, 11):
    from contextlib import chdir
else:

    @contextmanager
    def chdir(path: Path) -> Generator[None, None, None]:
        """Change directory context manager for Python < 3.11 compatibility."""
        original = Path.cwd()
        try:
            os.chdir(path)
            yield
        finally:
            os.chdir(original)


def call_app_with_chdir(
    app: typer.Typer,
    bakefile_path: Path | None,
    *args: Any,
    **kwargs: Any,
) -> None:
    if bakefile_path is not None:
        dir_path = bakefile_path.parent
        with chdir(dir_path):
            app(*args, **kwargs)
    else:
        app(*args, **kwargs)


def show_help_if_no_command(ctx: Context) -> None:
    if ctx.invoked_subcommand is None:
        console.echo(ctx.get_help())
        raise typer.Exit(1)
