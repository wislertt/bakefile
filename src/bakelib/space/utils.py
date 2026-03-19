import re
import subprocess
import sys
from enum import Enum
from pathlib import Path
from typing import Literal

from bake import Context, console
from bake.ui.logger.capsys import strip_ansi


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


def check_rust_version_matches_stable(ctx: Context):
    current_rust = ctx.run("rustc --version", echo=False, stream=False, capture_output=True)
    stable_rust = ctx.run(
        "rustup run stable rustc --version", echo=False, stream=False, capture_output=True
    )
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


def print_subprocess_output(result: subprocess.CompletedProcess[str] | None) -> None:
    if not result:
        return

    if result.stdout:
        console.err.print(f"[dim]stdout:[/dim] {strip_ansi(result.stdout)}")

    if result.stderr:
        console.err.print(f"[dim]stderr:[/dim] {strip_ansi(result.stderr)}")
