import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import zerv
from tenacity import RetryCallState, retry, retry_if_exception_type, stop_after_attempt

from bake import StrOrNoneCompletedProcess, console, style

from .base import BaseSpace
from .utils import check_rust_version_matches_stable

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def _cleanup_rustup_temp(retry_state: RetryCallState) -> None:
    _ = retry_state
    rustup_dir = Path.home() / ".rustup"
    dirs_to_remove: list[Path] = [
        rustup_dir / "tmp",
        rustup_dir / "downloads",
    ]

    for dir_path in dirs_to_remove:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            console.echo(f"Removed {dir_path}", highlight=False)


def run_rustup_update(
    run_fn: Callable[..., StrOrNoneCompletedProcess],
    timeout: float = 30,
    max_attempts: int = 5,
) -> None:

    @retry(
        stop=stop_after_attempt(max_attempts),
        retry=retry_if_exception_type(subprocess.TimeoutExpired),
        reraise=True,
        before_sleep=_cleanup_rustup_temp,
    )
    def _run():
        run_fn("rustup update", timeout=timeout)

    try:
        _run()
    except subprocess.TimeoutExpired:
        console.warning(
            f"{style.code('rustup update')} timed out after {max_attempts} attempts, skipping",
            highlight=False,
        )


class RustSpace(BaseSpace):
    def _get_mise_tools(self) -> set[str]:
        return super()._get_mise_tools() | {
            "aqua:cargo-bins/cargo-binstall",
            "aqua:rust-lang/rustup",
            "cargo:cargo-audit",
            "cargo:cargo-sort",
            "cargo:cargo-tarpaulin",
        }

    def _get_required_cli_tools(self) -> dict[str, set[Path] | None]:
        tools = super()._get_required_cli_tools()
        tools["rustup"] = None
        tools["rustc"] = None
        tools["cargo"] = None
        tools["cargo-audit"] = None
        tools["cargo-binstall"] = None
        tools["cargo-tarpaulin"] = None
        return tools

    def _setup_tools(self) -> None:
        super()._setup_tools()
        run_rustup_update(self.ctx.run)
        self.ctx.run("rustup install stable")

    def lint(self) -> None:
        super().lint()

        self.ctx.run("cargo sort")
        self.ctx.run("cargo +nightly check --tests")
        self.ctx.run("cargo +nightly fmt -- --check || (cargo +nightly fmt && exit 1)")
        self.ctx.run("cargo +nightly clippy --all-targets --all-features -- -D warnings")

    def _update_project(self) -> None:
        super()._update_project()
        run_rustup_update(self.ctx.run)
        self.ctx.run("cargo update")
        check_rust_version_matches_stable(self.ctx)

    def _get_cargo(self) -> dict[str, Any]:
        cargo_toml = Path("Cargo.toml")
        return tomllib.loads(cargo_toml.read_text())

    def _get_version_from_cargo_toml(self) -> str:
        return self._get_cargo()["package"]["version"]

    def _get_package_name_from_cargo_toml(self) -> str:
        return self._get_cargo()["package"]["name"]

    @property
    def _package_name(self) -> str:
        return self._get_package_name_from_cargo_toml()

    def _get_version(self) -> str:
        return self._get_version_from_cargo_toml()

    def _set_version(self, value: str) -> None:
        super()._set_version(value)
        self._set_version_in_cargo_toml(value)

    def _set_version_in_cargo_toml(self, version: str) -> None:
        version = zerv.render(version=version, output_format="semver")
        cargo_toml = Path("Cargo.toml")
        original_version = self._get_version_from_cargo_toml()
        content = cargo_toml.read_text()
        content = re.sub(
            r'(^version\s*=\s*)"[^"]*"',
            rf'\1"{version}"',
            content,
            count=1,
            flags=re.MULTILINE,
        )
        cargo_toml.write_text(content)
        console.echo(
            f"Cargo.toml: update [bold cyan]{self._package_name}[/bold cyan] "
            f"version {original_version} => {version}",
            highlight=False,
        )
