import shutil
from pathlib import Path

import pathspec
from pathspec.patterns.gitignore.basic import GitIgnoreBasicPattern

from bake.ui import console


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

    if path.is_dir():
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
