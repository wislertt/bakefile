import shutil
from pathlib import Path

import pathspec
from pathspec.patterns.gitignore.basic import GitIgnoreBasicPattern

from bake.ui import console


def remove_git_clean_candidates(
    git_clean_dry_ruu_output: str, exclude_patterns: set[str], dry_run: bool
) -> None:
    spec = pathspec.PathSpec.from_lines(
        GitIgnoreBasicPattern,
        exclude_patterns,
    )

    for line in git_clean_dry_ruu_output.splitlines():
        line = line.strip()
        if not line.startswith("Would remove "):
            continue

        rel_path = line.removeprefix("Would remove ").strip()
        path = Path(rel_path)

        if spec.match_file(rel_path):
            console.echo(f"[yellow]~[/yellow] Skipping {path}")
            continue

        if path.is_dir() and (path / ".git").exists():
            console.echo(f"[yellow]~[/yellow] Skipping git repository {path}")
            continue

        console.echo(f"[red]-[/red] [dim]Removing[/dim] {path}")

        if dry_run is True:
            continue

        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)
