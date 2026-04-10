import shutil
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, NoReturn

import orjson
import typer
import zerv

from bake import Bakebook, command, console, run
from bakelib.utils import CleanUtils

from .utils import (
    PlatformType,
    get_platform,
    install_mise_tools,
    orjson_default,
    setup_brew,
    setup_mise,
)


class BaseSpace(CleanUtils, Bakebook):
    @property
    def _package_name(self) -> str:
        self._method_not_available("_package_name")

    @property
    def _version(self) -> str:
        self._method_not_available("_version")

    @_version.setter
    def _version(self, value: str) -> None:
        self._version_setter(value)

    def _version_setter(self, value: str) -> None:
        _ = value
        self._method_not_available("_version")

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
        schema: zerv.StandardSchema = "standard-base-prerelease-post-dev",
    ) -> str:
        return (
            zerv.render(version=version, output_format=version_format)
            if version
            else zerv.flow(schema=schema, output_format=version_format)
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
        schema: zerv.StandardSchema = "standard-base-prerelease-post-dev",
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
        console.error(f"Command '{command_name}' is not available")
        raise typer.Exit(1)

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

    def setup_tool_managers(self, platform: PlatformType) -> None:
        _ = platform
        setup_brew(self.ctx)
        setup_mise(self.ctx)

    def _get_mise_tools(self) -> set[str]:
        return {
            "bun",
            "pipx:bakefile",
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

    def add_mise_tools(self) -> None:
        result = run(
            "mise list --local --current --json", stream=False, echo=False, capture_output=True
        )
        current_tools: set[str] = set()
        if result and result.stdout:
            data = orjson.loads(result.stdout)
            current_tools = set(data.keys())

        required_tools = self._get_mise_tools()
        missing_tools = sorted(required_tools - current_tools)

        if missing_tools:
            console.start("Adding missing mise tools")

        for tool in missing_tools:
            self.ctx.run(f"mise use {tool}")

    def setup_tools(self) -> None:
        self.add_mise_tools()
        install_mise_tools(self.ctx)

    def setup_project(self) -> None:
        self.ctx.run("pre-commit install")
        if self.ctx.obj.is_standalone_bakefile:
            self.ctx.run("bakefile sync --frozen")

    @command(help="Setup development environment")
    def setup_dev(self) -> None:
        platform = get_platform()
        console.echo(f"Detected platform: {platform}")

        if platform != "macos":
            console.warning(
                f"Platform '{platform}' is not officially supported. "
                "Tool manager setup will run in dry-run mode."
            )
            overridden_dry_run = True
        else:
            overridden_dry_run = self.ctx.dry_run

        console.start("Cleaning")
        self.clean(exclude_patterns=None, default_excludes=True)

        with self.ctx.override_dry_run(overridden_dry_run):
            console.start("Setting up tool managers")
            self.setup_tool_managers(platform=platform)

        console.start("Setting up tools")
        self.setup_tools()

        console.start("Setting up project")
        self.setup_project()

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
            typer.Option(
                "--fast",
                "-f",
                count=True,
                help="Skip steps: -f skips tests, -ff skips tests and lint",
            ),
        ] = 0,
    ) -> None:
        self._assert_tools()

        if fast < 2:
            console.start("Linting")
            self.lint()
        if fast < 1:
            console.start("Testing")
            self.test()

    @command(help="Upgrade all dependencies")
    def update(self) -> None:
        platform = get_platform()
        if platform == "macos":
            setup_brew(self.ctx)
        self.ctx.run("mise upgrade")
        self.ctx.run("uv python upgrade")
        self.ctx.run("uv tool upgrade --all")
        self.ctx.run("pre-commit autoupdate")
        if self.ctx.obj.is_standalone_bakefile:
            self.ctx.run("bakefile lock --upgrade")
            self.ctx.run("bakefile sync")
