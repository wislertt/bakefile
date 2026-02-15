import re
import sys
from pathlib import Path
from typing import Any

import zerv

from bake import console

from .base import BaseSpace
from .utils import check_rust_version_matches_stable

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]


class RustSpace(BaseSpace):
    def _get_mise_tools(self) -> set[str]:
        return super()._get_mise_tools() | {
            "aqua:cargo-bins/cargo-binstall",
            "aqua:rust-lang/rustup",
            "cargo:cargo-audit",
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

    def setup_tools(self) -> None:
        super().setup_tools()
        self.ctx.run("rustup update")
        self.ctx.run("rustup install stable")

    def lint(self) -> None:
        super().lint()

        self.ctx.run(
            "uv run toml-sort --sort-inline-arrays --sort-first=package --in-place Cargo.toml"
        )
        self.ctx.run("cargo +nightly check --tests")
        self.ctx.run("cargo +nightly fmt -- --check || (cargo +nightly fmt && exit 1)")
        self.ctx.run("cargo +nightly clippy --all-targets --all-features -- -D warnings")

    def update(self) -> None:
        super().update()
        self.ctx.run("rustup update")
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

    @property
    def _version(self) -> str:
        return self._get_version_from_cargo_toml()

    @_version.setter
    def _version(self, value: str) -> None:
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
