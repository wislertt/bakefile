import shutil
import sys
from enum import Enum
from pathlib import Path
from typing import Literal

import pathspec
from pathspec.patterns.gitignore.basic import GitIgnoreBasicPattern
from pydantic import BaseModel, Field

from bake import Context
from bake.ui import console


def setup_brew(ctx: Context) -> None:
    ctx.run("brew update")
    ctx.run("brew upgrade")
    ctx.run("brew cleanup")
    ctx.run("brew list")
    ctx.run("brew leaves")


class ToolInfo(BaseModel):
    version: str | None = None
    expected_paths: list[Path] = Field(default_factory=list, exclude=True)


class Platform(Enum):
    MACOS = "macos"
    LINUX = "linux"
    WINDOWS = "windows"
    OTHER = "other"


PlatformType = Literal["macos", "linux", "windows", "other"]


def get_platform() -> PlatformType:
    if sys.platform == "darwin":
        return Platform.MACOS.value
    elif sys.platform == "linux":
        return Platform.LINUX.value
    elif sys.platform == "win32":
        return Platform.WINDOWS.value
    return Platform.OTHER.value


def setup_uv(ctx: Context) -> None:
    ctx.run("brew install uv")
    ctx.run("uv python upgrade")
    ctx.run("uv tool upgrade --all")
    ctx.run("uv tool update-shell")


def setup_bun(ctx: Context) -> None:
    ctx.run("brew install oven-sh/bun/bun")


def setup_uv_tool(ctx: Context) -> None:
    ctx.run("uv tool install bakefile")
    ctx.run("uv tool install pre-commit")


HOMWBREW_BIN = Path("/opt/homebrew/bin")
LOCAL_BIN = Path.home() / ".local" / "bin"
VENV_BIN = Path.cwd() / ".venv" / "bin"


def get_expected_paths(tool: str, locations: set[Path]) -> list[Path]:
    return [loc / tool for loc in locations]


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
