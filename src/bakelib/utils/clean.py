import shutil
from pathlib import Path
from typing import Annotated

import pathspec
import typer
from pathspec.patterns.gitignore.basic import GitIgnoreBasicPattern

from bake import Bakebook, command, console


def _skip_msg(path: Path, suffix: str, dry_run: bool) -> None:
    verb = "Would skip" if dry_run else "Skipping"
    console.echo(f"[yellow]~[/yellow] {verb} {suffix}{path}")


def _remove_msg(path: Path, dry_run: bool) -> None:
    verb = "Would remove" if dry_run else "Removing"
    console.echo(f"[red]-[/red] [dim]{verb}[/dim] {path}")


def _should_remove_path(path: Path, dry_run: bool) -> None:
    _remove_msg(path, dry_run)
    if dry_run:
        return

    if path.is_symlink():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)


def remove_git_clean_candidates(
    git_clean_dry_run_output: str, exclude_patterns: set[str], dry_run: bool
) -> None:
    spec = pathspec.PathSpec.from_lines(
        GitIgnoreBasicPattern,
        exclude_patterns,
    )

    for line in git_clean_dry_run_output.splitlines():
        line = line.strip()
        if not line.startswith("Would remove "):
            continue

        rel_path = line.removeprefix("Would remove ").strip()
        path = Path(rel_path)

        if spec.match_file(rel_path):
            _skip_msg(path, "", dry_run)
            continue

        if path.is_dir() and (path / ".git").exists():
            _skip_msg(path, "git repository ", dry_run)
            continue

        _should_remove_path(path, dry_run)


class CleanUtils(Bakebook):
    def _clean(
        self,
        exclude_patterns: list[str] | None,
        default_excludes: bool,
        default_exclude_patterns: set[str],
    ):
        results = self.ctx.run("git clean -fdX -n", stream=False, echo=True, capture_output=True)

        exclude_patterns: set[str] = set(exclude_patterns if exclude_patterns else [])

        if default_excludes:
            exclude_patterns |= default_exclude_patterns

        console.err.print(f"Exclude pattens: {exclude_patterns}")

        remove_git_clean_candidates(
            git_clean_dry_run_output=results.stdout,
            exclude_patterns=exclude_patterns,
            dry_run=self.ctx.dry_run,
        )

    @command(help="Clean gitignored files with optional exclusions")
    def clean(
        self,
        exclude_patterns: Annotated[
            list[str] | None,
            typer.Option(
                "--exclude-patterns",
                "-e",
                help="Patterns to exclude",
            ),
        ] = None,
        default_excludes: Annotated[
            bool,
            typer.Option(help="Apply default exclude patterns (.env, .cache)"),
        ] = True,
    ) -> None:
        self._clean(
            exclude_patterns=exclude_patterns,
            default_excludes=default_excludes,
            default_exclude_patterns={".env", ".cache"},
        )

    @command(help="Clean all gitignored files")
    def clean_all(self) -> None:
        self.ctx.run("git clean -fdX")
