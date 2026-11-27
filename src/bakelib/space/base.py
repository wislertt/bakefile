import inspect
import os
import re
import shlex
import shutil
from collections.abc import Callable, Generator
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Annotated, NoReturn

import orjson
import typer
import zerv

from bake import Bakebook, Context, command, console
from bake._params import fast_option, slow_option
from bake.bakebook.bakebook import GroupKwargs
from bake.utils.constants import DEFAULT_BAKEBOOK_NAME, DEFAULT_FILE_NAME
from bake.utils.settings import PlatformType, bake_settings
from bakelib.managed_content import (
    EXIT_DRIFT,
    EXIT_ERROR,
    ManagedContent,
    ManagedFile,
    exit_on_error,
    read_file,
)
from bakelib.utils import CleanUtils

from .migration import Migration
from .utils import (
    Fetch,
    install_mise_tools,
    orjson_default,
    setup_brew,
    setup_mise,
)
from .utils.gitignore import GITHUB, Upstream, render_lines, stack_section

OXFMT_SUFFIXES = ("js", "jsx", "ts", "tsx", "css", "json", "json5", "yaml", "yml", "md")
PRETTIER_CONFIG_FILES = (
    ".prettierrc",
    ".prettierrc.json",
    ".prettierrc.json5",
    ".prettierrc.yaml",
    ".prettierrc.yml",
    ".prettierrc.toml",
    *(
        f"{stem}.{ext}"
        for stem in (".prettierrc", "prettier.config")
        for ext in ("js", "mjs", "cjs", "ts", "mts", "cts")
    ),
)


def _prettier_config_files() -> list[Path]:
    return [Path(name) for name in PRETTIER_CONFIG_FILES if Path(name).is_file()]


class RemovePrettierConfig(Migration):
    expires = date(2027, 2, 25)
    description = "Remove the prettier config, replaced by the managed oxfmt.config.ts"

    def check(self, ctx: Context) -> bool:
        _ = ctx
        return bool(_prettier_config_files())

    def apply(self, ctx: Context) -> None:
        # a Python delete, not `rm`, so it works on Windows too
        for path in _prettier_config_files():
            console.cmd(f"rm {path}")
            if not ctx.dry_run:
                path.unlink()


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


MANAGED_CONTENT_GROUP = "managed-content"


def _semver_normalize(value: str) -> str:
    return zerv.render(version=value, output_format="semver")


# mirrors mise's tool-arg grammar (src/cli/args/tool_arg.rs parse_input)
_MISE_TOOL_SPEC = re.compile(
    r"^(?P<name>(?:[^:@\[]+:)?(?:@[^@\[]+)?[^@\[]*)"
    r"(?:\[(?P<options>[^\]]*)\])?"
    r"(?:@(?P<version>.*))?$"
)


def _strip_mise_options(tool: str) -> str:
    # mise list keys are bare ids: no [options], no @version
    match = _MISE_TOOL_SPEC.match(tool)
    return match["name"] if match is not None else tool


def local_mise_tools(ctx: Context) -> set[str]:
    # read-only: run even in dry-run so a preview sees the real tools
    result = ctx.run(
        "mise list --local --current --json",
        stream=False,
        echo=False,
        capture_output=True,
        clean_capture_output=False,  # parsed as JSON below
        dry_run=False,
        check=False,
    )
    if not result or not result.stdout:
        return set()
    return {_strip_mise_options(tool) for tool in orjson.loads(result.stdout)}


def _raised_in_get_migrations(error: KeyError) -> bool:
    # a dead `del` fails in C, so its innermost Python frame is the override itself
    tb = error.__traceback__
    while tb is not None and tb.tb_next is not None:
        tb = tb.tb_next
    return tb is not None and tb.tb_frame.f_code.co_name == "_get_migrations"


def _defined_in_project(migration: Migration) -> bool:
    # upstream Spaces live in site-packages; an editable install or bakefile.py lives in the repo
    source = inspect.getsourcefile(type(migration))
    if source is None:
        return False
    path = Path(source).resolve()
    return path.is_relative_to(Path.cwd().resolve()) and "site-packages" not in path.parts


def _class_location(migration: Migration) -> str:
    cls = type(migration)
    source = Path(inspect.getsourcefile(cls) or "").resolve()
    if source.is_relative_to(Path.cwd().resolve()):
        source = source.relative_to(Path.cwd().resolve())
    return f"{cls.__qualname__} in {source.as_posix()}:{inspect.getsourcelines(cls)[1]}"


class BaseSpace(CleanUtils, Bakebook):
    bake_manage_content: bool = False

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
    def lint(
        self,
        slow: Annotated[int, slow_option(help="Add slow steps: -s runs every check")] = 0,
    ) -> None:
        self._lint_fast()
        if slow >= 1:
            self._lint_slow()

    def _lint_fast(self) -> None:
        self._fail_on_expired_migrations()
        self._fail_on_pending_migrations()
        # before any formatter, so drift is reported against the files as committed
        if self.bake_manage_content:
            content = self._managed_content(Fetch.NEVER)
            content.lock(dry_run=self.ctx.dry_run)
            content.check()
        self.ctx.run(f'oxfmt "**/*.{{{",".join(OXFMT_SUFFIXES)}}}"')
        for mise_toml in (Path(".mise.toml"), Path("mise.toml")):
            if not mise_toml.exists():
                continue
            self.ctx.run(
                f"uv run toml-sort --sort-inline-arrays --in-place --sort-table-keys {mise_toml}"
            )
        if self.ctx.obj.is_standalone_bakefile:
            self._lint_standalone_bakefile()

    def _lint_slow(self) -> None:
        # Hook for subclasses: the base has no slow checks, so `lint -s` adds nothing here
        pass

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
            "npm:oxfmt",
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
        current_tools = local_mise_tools(self.ctx)
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
        if self.bake_manage_content:
            # before the clean: it may remove the venv bake runs from, templates included
            console.start("Syncing managed content")
            self._run_managed_sync(dry_run=self.ctx.dry_run, force=False)
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
        self._apply_migrations()
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
            self.lint(slow=1)  # top lint level: raise it when lint gains a level
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
        if self.bake_manage_content:
            # lock with the outgoing templates, before upgrades replace them
            self._run_managed_lock()
        if fast < 1:
            console.start("Upgrading platform tools")
            with self._platform_tools_context() as platform:
                self._update_platform_tools(platform)
        if fast < 2:
            console.start("Upgrading tools")
            self._update_tools()
        console.start("Upgrading project")
        self._update_project()
        # a fresh process imports the Migrations and templates the upgrades just installed
        self.ctx.run(self._bake_command("post-update"))

    @command(name="post-update", hidden=True, help="Finish `bake update` with the upgraded code")
    def post_update(self) -> None:
        self._apply_migrations()
        if self.bake_manage_content:
            console.start("Syncing managed content")
            self._run_managed_sync(dry_run=self.ctx.dry_run, force=False, refresh=True)

    def _get_migrations(self) -> dict[str, Migration]:
        return {"remove-prettier-config": RemovePrettierConfig()}

    def collect_migrations(self) -> dict[str, Migration]:
        try:
            return self._get_migrations()
        except KeyError as e:
            if not _raised_in_get_migrations(e):
                raise
            key = e.args[0] if e.args else ""
            console.error(
                f"_get_migrations() removes Migration {key!r}, which no longer exists upstream, "
                "so delete that line",
                markup=False,
            )
            raise typer.Exit(EXIT_ERROR) from None

    def _pending_migrations(self) -> dict[str, Migration]:
        migrations = self.collect_migrations()
        return {key: m for key, m in migrations.items() if m.check(self.ctx)}

    def _fail_on_expired_migrations(self) -> None:
        today = date.today()
        expired = {
            key: migration
            for key, migration in self.collect_migrations().items()
            if migration.expires < today and _defined_in_project(migration)
        }
        if not expired:
            return
        for key, migration in expired.items():
            console.error(
                f"Migration {key} ({_class_location(migration)}) expired on "
                f"{migration.expires.isoformat()}: {migration.description}",
                markup=False,
            )
        console.error(
            "remove each expired Migration: its class and its key in _get_migrations()",
            markup=False,
        )
        raise typer.Exit(EXIT_DRIFT)

    def _fail_on_pending_migrations(self) -> None:
        pending = self._pending_migrations()
        if not pending:
            return
        for key, migration in pending.items():
            console.error(f"Migration {key} applies: {migration.description}", markup=False)
        console.error(
            "run `bake setup-dev` (or `bake update`) to apply pending Migrations", markup=False
        )
        raise typer.Exit(EXIT_DRIFT)

    def _apply_migrations(self) -> None:
        pending = self._pending_migrations()
        if not pending:
            return
        console.start("Applying migrations")
        for key, migration in pending.items():
            console.info(f"{key}: {migration.description}", markup=False)
            try:
                migration.apply(self.ctx)
            except Exception as e:
                console.error(f"Migration {key} failed: {e}", markup=False)
                raise typer.Exit(EXIT_ERROR) from e

    def _get_managed_files(self) -> dict[str, ManagedFile]:
        return {
            ".gitignore": ManagedFile(__package__, "gitignore"),
            "oxfmt.config.ts": ManagedFile(__package__, "oxfmt-config.ts"),
        }

    def _get_managed_values(self, fetch: Fetch) -> dict[str, str]:
        gitignore = self._get_managed_files().get(".gitignore")
        if gitignore is None or gitignore.detached:
            # nothing renders the section, so it must not fetch
            fetch = Fetch.NEVER
        return {
            "gitignore_stack_section": stack_section(
                read_file(Path.cwd(), ".gitignore"),
                self._get_gitignore_templates(),
                fetch,
                self._get_gitignore_upstream(),
            ),
            "gitignore_lines_section": render_lines(self._get_gitignore_lines()),
        }

    def _get_gitignore_templates(self) -> set[str]:
        # every repo runs bakefile.py, which leaves __pycache__/ behind
        return {"Global/macOS", "Global/Windows", "Global/VisualStudioCode", "Python"}

    def _get_gitignore_upstream(self) -> Upstream:
        return GITHUB

    def _get_gitignore_lines(self) -> set[str]:
        return {
            ".env*",
            "*.local.md",
            "*.local.toml",
            ".claude/settings.local.json",
            ".claude/worktrees/",
            ".playwright-mcp/",
            ".scratch",
            "**/.ssh/id_*",
            "**/.ssh/*_id_*",
            "**/.ssh/known_hosts",
        }

    def _managed_content(self, fetch: Fetch) -> ManagedContent:
        with exit_on_error():
            # a child Space's insert or set_default raises here
            managed_files = self._get_managed_files()
            values = self._get_managed_values(fetch)
        return ManagedContent(Path.cwd(), managed_files, values)

    def _bake_command(self, args: str) -> str:
        obj = self.ctx.obj
        options = ""
        if obj.chdir is not None:
            options += f" --chdir {shlex.quote(str(obj.chdir))}"
        if obj.use_global:
            options += " --global"
        if obj.file_name != DEFAULT_FILE_NAME:
            options += f" --file-name {shlex.quote(obj.file_name)}"
        if obj.bakebook_name != DEFAULT_BAKEBOOK_NAME:
            options += f" --book-name {shlex.quote(obj.bakebook_name)}"
        return f"bake{options} {args}"

    def _run_managed_lock(self, *, rebuild: bool = False) -> None:
        self._managed_content(Fetch.NEVER).lock(dry_run=self.ctx.dry_run, rebuild=rebuild)

    def _run_managed_sync(self, *, dry_run: bool, force: bool, refresh: bool = False) -> None:
        fetch = Fetch.REFRESH if refresh else Fetch.WHEN_NEEDED
        self._managed_content(fetch).sync(dry_run=dry_run, force=force)

    def get_group_kwargs(self) -> dict[str, GroupKwargs]:
        group_kwargs = super().get_group_kwargs()
        group_kwargs[MANAGED_CONTENT_GROUP] = GroupKwargs(
            help="Write and check files Spaces manage (alias: mc)", aliases=("mc",)
        )
        return group_kwargs

    def _require_managed_content(self) -> None:
        if self.bake_manage_content:
            return
        console.error(
            "managed content is off: set `bake_manage_content: bool = True` on your Bakebook "
            "in bakefile.py, or BAKE_MANAGE_CONTENT=true"
        )
        raise typer.Exit(EXIT_ERROR)

    @command(name="lock", group_name=MANAGED_CONTENT_GROUP, help="Rebuild bake.lock from the files")
    def managed_content_lock(self) -> None:
        self._require_managed_content()
        self._run_managed_lock(rebuild=True)

    @command(name="sync", group_name=MANAGED_CONTENT_GROUP, help="Write managed files")
    def managed_content_sync(
        self,
        dry_run: Annotated[
            bool, typer.Option("--dry-run", help="Show what would change, write nothing")
        ] = False,
        force: Annotated[
            bool, typer.Option("--force", help="Overwrite files that do not match their template")
        ] = False,
        refresh: Annotated[
            bool,
            typer.Option(
                "--refresh",
                help="Fetch values that come from the network again, from their latest upstream",
            ),
        ] = False,
    ) -> None:
        self._require_managed_content()
        self._run_managed_sync(dry_run=dry_run or self.ctx.dry_run, force=force, refresh=refresh)
