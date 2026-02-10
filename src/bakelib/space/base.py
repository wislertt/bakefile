from pathlib import Path
from typing import Annotated, Literal, NoReturn

import orjson
import typer

from bake import Bakebook, command
from bake.ui import console

from .utils import (
    HOMWBREW_BIN,
    LOCAL_BIN,
    VENV_BIN,
    PlatformType,
    ToolInfo,
    get_expected_paths,
    get_platform,
    remove_git_clean_candidates,
    setup_brew,
    setup_bun,
    setup_uv,
    setup_uv_tool,
)


class BaseSpace(Bakebook):
    def _no_implementation(self) -> None:
        console.error("No implementation")
        raise typer.Exit(1)

    def _not_implemented(self, method_name: str) -> NoReturn:
        raise NotImplementedError(f"{self.__class__.__name__} must implement {method_name}()")

    @command(help="Run linters and formatters")
    def lint(self) -> None:
        self.ctx.run(
            'bunx prettier@latest --write "**/*.{js,jsx,ts,tsx,css,json,json5,yaml,yml,md}"'
        )

    @command(help="Run unit tests")
    def test(self) -> None:
        self._no_implementation()

    @command(help="Run integration tests")
    def test_integration(self) -> None:
        self._no_implementation()

    @command(help="Run all tests")
    def test_all(self) -> None:
        self._no_implementation()

    def _clean(
        self,
        exclude_patterns: list[str] | None,
        default_excludes: bool,
        default_exclude_patterns: set[str],
    ):
        results = self.ctx.run("git clean -fdX -n", stream=False, dry_run=False, echo=True)

        exclude_patterns: set[str] = set(exclude_patterns if exclude_patterns else [])

        if default_excludes:
            exclude_patterns |= default_exclude_patterns

        console.err.print(f"Exclude pattens: {exclude_patterns}")

        remove_git_clean_candidates(
            git_clean_dry_run_output=results.stdout,
            exclude_patterns=exclude_patterns,
            dry_run=self.ctx.dry_run,
        )

    @command(help="Clean gitignored files with optional exclusions")
    def clean(
        self,
        exclude_patterns: Annotated[
            list[str] | None,
            typer.Option(
                "--exclude-patterns",
                "-e",
                help="Patterns to exclude",
            ),
        ] = None,
        default_excludes: Annotated[
            bool,
            typer.Option(help="Apply default exclude patterns (.env, .cache)"),
        ] = True,
    ) -> None:
        self._clean(
            exclude_patterns=exclude_patterns,
            default_excludes=default_excludes,
            default_exclude_patterns={".env", ".cache"},
        )

    @command(help="Clean all gitignored files")
    def clean_all(self) -> None:
        self.ctx.run("git clean -fdX")

    def setup_tool_managers(self, platform: PlatformType) -> None:
        _ = platform
        setup_brew(self.ctx)

    def setup_tools(self, platform: PlatformType) -> None:
        _ = platform
        setup_bun(self.ctx)
        setup_uv(self.ctx)
        setup_uv_tool(self.ctx)

    def setup_project(self) -> None:
        self.ctx.run("uv run pre-commit install")

    @command(help="Setup development environment")
    def setup_dev(self) -> None:
        platform = get_platform()
        console.echo(f"Detected platform: {platform}")

        if platform != "macos":
            console.warning(f"Platform '{platform}' is not supported. Running in dry-run mode.")
            overridden_dry_run = True
        else:
            overridden_dry_run = self.ctx.dry_run

        with self.ctx.override_dry_run(overridden_dry_run):
            self.clean(exclude_patterns=None, default_excludes=True)

        with self.ctx.override_dry_run(overridden_dry_run):
            self.setup_tool_managers(platform=platform)
            self.setup_tools(platform=platform)
            self.setup_project()

    def _assert_which_path(
        self,
        tool_name: str,
        tool_info: ToolInfo,
    ) -> bool:
        result = self.ctx.run(f"which {tool_name}", stream=False)
        if self.ctx.dry_run:
            return True
        actual_path = Path(result.stdout.strip())

        if actual_path in set(tool_info.expected_paths):
            console.success(f"{tool_name}: {actual_path}")
            return True

        console.warning(f"{tool_name}: unexpected location (got {actual_path})")
        return False

    def _get_tools(self) -> dict[str, ToolInfo]:
        return {
            # homebrew only
            "bun": ToolInfo(expected_paths=get_expected_paths("bun", {HOMWBREW_BIN})),
            # homebrew or venv
            "uv": ToolInfo(expected_paths=get_expected_paths("uv", {HOMWBREW_BIN, VENV_BIN})),
            # local or venv
            "bakefile": ToolInfo(
                expected_paths=get_expected_paths("bakefile", {LOCAL_BIN, VENV_BIN})
            ),
            "pre-commit": ToolInfo(
                expected_paths=get_expected_paths("pre-commit", {LOCAL_BIN, VENV_BIN})
            ),
        }

    @command(help="List development tools")
    def tools(
        self,
        format: Annotated[
            Literal["json", "names"],
            typer.Option("--format", "-f", help="Output format"),
        ] = "json",
    ) -> None:
        tools = self._get_tools()
        if format == "json":
            output: dict[str, dict[str, str | None]] = {k: v.model_dump() for k, v in tools.items()}
            console.echo(orjson.dumps(output, option=orjson.OPT_INDENT_2).decode())
        else:
            console.echo("\n".join(sorted(tools.keys())))

    @command(help="Assert development environment setup")
    def assert_setup_dev(
        self,
        skip_test: Annotated[
            bool,
            typer.Option(
                "--skip-test",
                "-s",
                help="Skip running tests",
            ),
        ] = False,
    ) -> None:
        tools = self._get_tools()
        for tool_name, tool_info in tools.items():
            self._assert_which_path(tool_name, tool_info)

        self.lint()
        if not skip_test:
            self.test()

    @command(help="Upgrade all dependencies")
    def update(self) -> None:
        self.ctx.run("uv python upgrade")
        self.ctx.run("uv tool upgrade --all")

    def package_name(self) -> str:
        self._not_implemented("package_name")

    @command()
    def version(self) -> str:
        self._not_implemented("version")
