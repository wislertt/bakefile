import re
import shutil
import sys
from enum import Enum
from pathlib import Path
from typing import Literal

import pathspec
from pathspec.patterns.gitignore.basic import GitIgnoreBasicPattern

from bake import Context, console


class Platform(Enum):
    MACOS = "macos"
    LINUX = "linux"
    WINDOWS = "windows"
    OTHER = "other"


VENV_BIN = Path.cwd() / ".venv" / "bin"


PlatformType = Literal["macos", "linux", "windows", "other"]


def orjson_default(obj):
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, set):
        return list(obj)
    raise TypeError


def setup_brew(ctx: Context) -> None:
    ctx.run("brew update")
    ctx.run("brew upgrade")
    ctx.run("brew cleanup")
    ctx.run("brew list")
    ctx.run("brew leaves")


def get_platform() -> PlatformType:
    if sys.platform == "darwin":
        return Platform.MACOS.value
    elif sys.platform == "linux":
        return Platform.LINUX.value
    elif sys.platform == "win32":
        return Platform.WINDOWS.value
    return Platform.OTHER.value


def setup_mise(ctx: Context) -> None:
    ctx.run("brew install mise")


def install_mise_tools(ctx: Context) -> None:
    ctx.run("mise install")
    ctx.run("mise doctor")
    ctx.run("mise list --local")
    ctx.run("mise upgrade")


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


def check_rust_version_matches_stable(ctx: Context):
    current_rust = ctx.run("rustc --version", echo=False, stream=False)
    stable_rust = ctx.run("rustup run stable rustc --version", echo=False, stream=False)
    if current_rust.stdout == stable_rust.stdout:
        return

    current_match = re.search(r"rustc (\d+\.\d+\.\d+)", current_rust.stdout)
    stable_match = re.search(r"rustc (\d+\.\d+\.\d+)", stable_rust.stdout)

    if current_match and stable_match:
        current = current_match.group(1)
        stable = stable_match.group(1)
    else:
        current = current_rust.stdout.strip()
        stable = stable_rust.stdout.strip()

    console.warning(
        f"Current Rust version ({current}) differs from stable ({stable}). "
        f"Update rust-toolchain.toml to stable version."
    )
