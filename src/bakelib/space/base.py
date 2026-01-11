from typing import Annotated

import typer

from bake import Bakebook, Context, command
from bake.ui import console

from .utils import remove_git_clean_candidates


class BaseSpace(Bakebook):
    @command(help="Run linters and formatters")
    def lint(self, ctx: Context) -> None:
        ctx.run(["bunx", "prettier@latest", "--write", "**/*.{js,jsx,ts,tsx,css,json,yaml,yml,md}"])

    @command(help="Run unit tests")
    def test(self) -> None:
        console.error("No implementation")
        raise typer.Exit(1)

    @command(help="Clean gitignored files with optional exclusions")
    def clean(
        self,
        ctx: Context,
        exclude_patterns: Annotated[
            list[str] | None,
            typer.Option(
                "--exclude-patterns",
                "-e",
                help="Patterns to exclude",
            ),
        ] = None,
        use_default_excludes: Annotated[
            bool,
            typer.Option(
                "--no-default-excludes",
                help="Do not apply default exclude patterns",
                is_flag=True,
            ),
        ] = False,
    ) -> None:
        results = ctx.run("git clean -fdX -n", stream=False, dry_run=False, echo=True)

        exclude_patterns: set[str] = set(exclude_patterns if exclude_patterns else [])

        if not use_default_excludes:
            exclude_patterns |= {".env", ".cache"}

        console.err.print(f"Exclude pattens: {exclude_patterns}")

        remove_git_clean_candidates(
            git_clean_dry_run_output=results.stdout,
            exclude_patterns=exclude_patterns,
            dry_run=ctx.dry_run,
        )

    @command(help="Clean all gitignored files")
    def clean_all(self, ctx: Context) -> None:
        ctx.run("git clean -fdX")

    @command(help="Setup development environment")
    def setup_dev(self) -> None:
        console.error("No implementation")
        raise typer.Exit(1)
