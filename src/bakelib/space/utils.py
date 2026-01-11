import shutil
from pathlib import Path

import pathspec
from pathspec.patterns.gitignore.basic import GitIgnoreBasicPattern

from bake.ui import console


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
            skip_msg = "Would skip" if dry_run else "Skipping"
            console.echo(f"[yellow]~[/yellow] {skip_msg} {path}")
            continue

        if path.is_dir() and (path / ".git").exists():
            skip_msg = "Would skip" if dry_run else "Skipping"
            console.echo(f"[yellow]~[/yellow] {skip_msg} git repository {path}")
            continue

        remove_msg = "Would remove" if dry_run else "Removing"
        console.echo(f"[red]-[/red] [dim]{remove_msg}[/dim] {path}")

        if dry_run is True:
            continue

        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)
