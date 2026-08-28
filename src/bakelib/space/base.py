import os
import shutil
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, NoReturn

import orjson
import typer
import zerv

from bake import Bakebook, command, console
from bake._params import fast_option
from bake.utils.settings import PlatformType, bake_settings
from bakelib.utils import CleanUtils

from .utils import (
    install_mise_tools,
    orjson_default,
    setup_brew,
    setup_mise,
)


def command_not_available(command_name: str) -> None:
    console.error(f"Command '{command_name}' is not available")
    raise typer.Exit(1)


def _global_keyring_env() -> dict[str, str]:
    # Prepend the global `keyring` dir so uv's subprocess provider resolves it
    # instead of the backend-less copy in a project/dev venv (via bakefile[lib]).
    path = os.environ.get("PATH", "")
    for entry in path.split(os.pathsep):
        if not entry:
            continue
        # Skip any directory inside a `.venv` (.venv/bin on POSIX,
        # .venv/Scripts on Windows) so we don't pick the venv-local keyring.
        if any(part == ".venv" for part in Path(entry).parts):
            continue
        if (Path(entry) / "keyring").exists():
            return {"PATH": f"{entry}{os.pathsep}{path}"}
    return {}


def _semver_normalize(value: str) -> str:
    return zerv.render(version=value, output_format="semver")


def _strip_mise_options(tool: str) -> str:
    # mise reports installed tools by bare id; inline options like
    # "pipx:bakefile[extras=locked]" never appear in `mise list` keys
    return tool.split("[", 1)[0]


class BaseSpace(CleanUtils, Bakebook):
    _version_schema: zerv.StandardSchema = "standard-base-prerelease-post-dev"

    @property
    def _package_name(self) -> str:
        self._method_not_available("_package_name")

    @property
    def _version(self) -> str:
        return self._get_version()

    @_version.setter
    def _version(self, value: str) -> None:
        self._set_version(value)

    # Asymmetric by design: getter raises NIE (base has no version source, so
    # reaching it is a bug), setter no-ops as a cooperative-super terminal.
    def _get_version(self) -> str:
        self._method_not_available("_version")

    def _set_version(self, value: str) -> None:
        pass

    # Explicit source list, never super(): base has no getter value (NIE above).
    # Default normalizes to semver so raw format variants compare equal.
    # Returns first source's raw value: tuple order picks the returned format.
    def _get_consistent_version(
        self,
        sources: tuple[type["BaseSpace"], ...],
        *,
        normalize: Callable[[str], str] = _semver_normalize,
    ) -> str:
        values = [source._get_version(self) for source in sources]
        if not values:
            self._method_not_available("_version")
        keys = [normalize(value) for value in values]
        if len(set(keys)) > 1:
            names = [source.__name__ for source in sources]
            raise ValueError(f"Version mismatch: {dict(zip(names, values, strict=True))}")
        return values[0]

    @command(help="Show or set current version")
    def version(
        self,
        version: Annotated[
            str | None,
            typer.Argument(help="Version value to set"),
        ] = None,
    ) -> None:
        if version is None:
            console.echo(self._version)
        else:
            self._version = version

    def _determine_new_version(
        self,
        version: str | None,
        version_format: zerv.OutputFormat = "semver",
        schema: zerv.StandardSchema | None = None,
    ) -> str:
        effective_schema = schema or self._version_schema
        return (
            zerv.render(version=version, output_format=version_format)
            if version
            else zerv.flow(schema=effective_schema, output_format=version_format)
        )

    @contextmanager
    def _optional_version_context(
        self,
        version: str | None,
    ):
        original_version = self._version
        did_change = False
        if version is not None:
            self._version = version
            did_change = True
        try:
            yield
        finally:
            if did_change:
                self._version = original_version

    @contextmanager
    def _version_bump_context(
        self,
        version: str | None,
        version_format: zerv.OutputFormat = "semver",
        schema: zerv.StandardSchema | None = None,
    ):
        original_version = self._version
        new_version = self._determine_new_version(
            version=version, version_format=version_format, schema=schema
        )
        self._version = new_version
        try:
            yield
        finally:
            self._version = original_version

    def _command_not_available(self, command_name: str) -> None:
        command_not_available(command_name)

    def _method_not_available(self, method_name: str) -> NoReturn:
        raise NotImplementedError(f"{self.__class__.__name__} must implement {method_name}()")

    def _lint_standalone_bakefile(self) -> None:
        self.ctx.run("bakefile lint")

    @command(help="Run linters and formatters")
    def lint(self) -> None:
        self.ctx.run(
            'bunx prettier@latest --write "**/*.{js,jsx,ts,tsx,css,json,json5,yaml,yml,md}"'
        )
        for mise_toml in (Path(".mise.toml"), Path("mise.toml")):
            if not mise_toml.exists():
                continue
            self.ctx.run(
                f"uv run toml-sort --sort-inline-arrays --in-place --sort-table-keys {mise_toml}"
            )
        if self.ctx.obj.is_standalone_bakefile:
            self._lint_standalone_bakefile()

    @command(help="Run unit tests")
    def test(self) -> None:
        self._command_not_available("test")

    @command(help="Run integration tests")
    def test_integration(self) -> None:
        self._command_not_available("test_integration")

    @command(help="Run all tests")
    def test_all(self) -> None:
        self._command_not_available("test_all")

    def _get_supported_platforms(self) -> set[PlatformType]:
        return {"macos"}

    @contextmanager
    def _platform_tools_context(self) -> Generator[PlatformType]:
        platform = bake_settings.platform
        console.echo(f"Detected platform: {platform}")
        if platform not in self._get_supported_platforms():
            console.warning(
                f"Platform '{platform}' is not officially supported. "
                "Platform tool setup will run in dry-run mode."
            )
            overridden_dry_run = True
        else:
            overridden_dry_run = self.ctx.dry_run

        with self.ctx.override_dry_run(overridden_dry_run):
            yield platform

    def _setup_platform_tools(self, platform: PlatformType) -> None:
        _ = platform
        setup_brew(self.ctx)
        setup_mise(self.ctx)

    def _get_mise_tools(self) -> set[str]:
        return {
            "bun",
            "pipx:bakefile[extras=locked]",
            "pipx:toml-sort",
            "pipx:zerv-version",
            "pipx:pre-commit",
            "uv",
        }

    def _get_required_cli_tools(self) -> dict[str, set[Path] | None]:
        return {
            # global - any location
            "bake": None,
            "bakefile": None,
            "bun": None,
            "bunx": None,
            "pre-commit": None,
            "uv": None,
            "zerv": None,
        }

    def _add_mise_tools(self) -> None:
        result = self.ctx.run(
            "mise list --local --current --json", stream=False, echo=False, capture_output=True
        )
        current_tools: set[str] = set()
        if result and result.stdout:
            data = orjson.loads(result.stdout)
            current_tools = {_strip_mise_options(tool) for tool in data}

        required_tools = self._get_mise_tools()
        missing_tools = sorted(
            tool for tool in required_tools if _strip_mise_options(tool) not in current_tools
        )

        if missing_tools:
            console.start("Adding missing mise tools")

        for tool in missing_tools:
            self.ctx.run(f"mise use '{tool}'")

    def _setup_tools(self) -> None:
        self._add_mise_tools()
        install_mise_tools(self.ctx)

    def _setup_project(self) -> None:
        console.start("Cleaning")
        self.clean(exclude_patterns=None, default_excludes=True)
        self.ctx.run("pre-commit install")
        if self.ctx.obj.is_standalone_bakefile:
            self.ctx.run("bakefile sync --frozen")

    @command(help="Setup development environment")
    def setup_dev(
        self,
        fast: Annotated[
            int,
            fast_option(help="Skip steps: -f skips platform tools, -ff also skips tools"),
        ] = 0,
    ) -> None:
        if fast < 1:
            console.start("Setting up platform tools")
            with self._platform_tools_context() as platform:
                self._setup_platform_tools(platform)
        if fast < 2:
            console.start("Setting up tools")
            self._setup_tools()
        console.start("Setting up project")
        self._setup_project()

    def _assert_which_path(
        self,
        tool_name: str,
        tool_paths: set[Path] | None,
    ) -> bool:
        console.cmd(f"which {tool_name}")
        if self.ctx.dry_run:
            return True

        actual_path = shutil.which(tool_name)
        if actual_path is None:
            console.error(f"{tool_name}: not found in PATH")
            return False

        actual_path = Path(actual_path).absolute()

        if tool_paths is None:
            console.success(f"{tool_name}: {actual_path}")
            return True

        for path_prefix in tool_paths:
            if actual_path.is_relative_to(path_prefix.absolute()):
                console.success(f"{tool_name}: {actual_path}")
                return True

        console.warning(f"{tool_name}: unexpected location (got {actual_path})")
        return False

    def _assert_tools(self):
        tools = self._get_required_cli_tools()
        if tools:
            console.start("Asserting required CLI tools")
        for tool_name, tool_paths in tools.items():
            self._assert_which_path(tool_name, tool_paths)

    @command(help="List development tools")
    def tools(
        self,
        json: Annotated[
            bool,
            typer.Option("--json", "-j", help="Output as JSON"),
        ] = False,
    ) -> None:
        tools = self._get_required_cli_tools()
        if json:
            console.echo(
                orjson.dumps(tools, default=orjson_default, option=orjson.OPT_INDENT_2).decode()
            )
        else:
            console.echo("\n".join(sorted(tools.keys())))

    @command(help="Assert development environment setup")
    def assert_setup_dev(
        self,
        fast: Annotated[
            int,
            fast_option(help="Skip steps: -f skips tests, -ff skips tests and lint"),
        ] = 0,
    ) -> None:
        self._assert_tools()

        if fast < 2:
            console.start("Linting")
            self.lint()
        if fast < 1:
            console.start("Testing")
            self.test()

    def _update_platform_tools(self, platform: PlatformType) -> None:
        _ = platform
        setup_brew(self.ctx)

    def _update_tools(self) -> None:
        self.ctx.run("mise upgrade")
        self.ctx.run("uv python upgrade")
        self.ctx.run("uv tool upgrade --all", env=_global_keyring_env())

    def _update_project(self) -> None:
        self.ctx.run("pre-commit autoupdate")
        if self.ctx.obj.is_standalone_bakefile:
            self.ctx.run("bakefile lock --upgrade")
            self.ctx.run("bakefile sync")

    @command(help="Upgrade all dependencies")
    def update(
        self,
        fast: Annotated[
            int,
            fast_option(
                help="Skip steps: -f skips platform tool upgrades, -ff also skips tool upgrades"
            ),
        ] = 0,
    ) -> None:
        if fast < 1:
            console.start("Upgrading platform tools")
            with self._platform_tools_context() as platform:
                self._update_platform_tools(platform)
        if fast < 2:
            console.start("Upgrading tools")
            self._update_tools()
        console.start("Upgrading project")
        self._update_project()
