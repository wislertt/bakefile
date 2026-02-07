import re
import sys
from pathlib import Path
from typing import Any

from bake import Context, console

from .base import BaseSpace, ToolInfo
from .utils import CARGO_BIN, HOMWBREW_BIN, get_expected_paths

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]


class RustSpace(BaseSpace):
    def _get_tools(self) -> dict[str, ToolInfo]:
        tools = super()._get_tools()
        tools["rustup"] = ToolInfo(
            version=None,
            expected_paths=list(get_expected_paths("rustup", {HOMWBREW_BIN})),
        )
        tools["cargo"] = ToolInfo(
            version=None,
            expected_paths=list(get_expected_paths("cargo", {HOMWBREW_BIN, CARGO_BIN})),
        )
        return tools

    def lint(self, ctx: Context) -> None:
        super().lint(ctx=ctx)

        ctx.run("cargo +nightly check --tests")
        ctx.run("cargo +nightly fmt -- --check || (cargo +nightly fmt && exit 1)")
        ctx.run("cargo +nightly clippy --all-targets --all-features -- -D warnings")

    def update(self, ctx: Context) -> None:
        super().update(ctx)
        ctx.run("rustup update")
        ctx.run("cargo update")

    def _get_cargo(self) -> dict[str, Any]:
        cargo_toml = Path("Cargo.toml")
        return tomllib.loads(cargo_toml.read_text())

    def package_name(self) -> str:
        return self._get_cargo()["package"]["name"]

    def current_version(self) -> str:
        return self._get_cargo()["package"]["version"]

    def _set_version(self, version: str) -> None:
        cargo_toml = Path("Cargo.toml")
        original_version = self.current_version()
        content = cargo_toml.read_text()
        content = re.sub(
            r'(^version\s*=\s*)"[^"]*"',
            rf'\1"{version}"',
            content,
            count=1,
            flags=re.MULTILINE,
        )
        cargo_toml.write_text(content)
        console.echo(f"{self.package_name()}-version {original_version} => {version}")
