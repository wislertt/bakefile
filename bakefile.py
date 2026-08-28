import logging
from pathlib import Path
from textwrap import dedent
from typing import Annotated

import typer
import zerv

from bake import (
    DEFAULT_BAKE_LOG,
    DEFAULT_BAKE_LOG_PRETTY,
    CliTask,
    ParallelCliTaskRunner,
    command,
    console,
    params,
    spawn_env,
)
from bakelib import GitHubActionsTools, PythonLibSpace
from scripts.locked_pins import (
    PYPROJECT_PATH,
    UV_LOCK_PATH,
    guard_invariants,
    locked_pin_specs,
    parse_lock_versions,
    relax_locked_pins,
    rewrite_locked_pins,
)

logger = logging.getLogger(__name__)


class MyBakebook(GitHubActionsTools, PythonLibSpace):
    bake_log: str = DEFAULT_BAKE_LOG
    bake_log_verbosity: params.BakeLogVerbosityField = 3
    bake_log_pretty: bool = DEFAULT_BAKE_LOG_PRETTY

    def _get_mise_tools(self) -> set[str]:
        mise_tools = super()._get_mise_tools()
        mise_tools.remove("pipx:bakefile[extras=locked]")
        mise_tools.add("npm:mintlify")
        return mise_tools

    def _update_project(self) -> None:
        super()._update_project()
        self._update_locked_pins()
        self._update_examples()
        self._update_hooks()

    def _update_locked_pins(self) -> None:
        original_text = PYPROJECT_PATH.read_text()
        relaxed_text, relaxed = relax_locked_pins(original_text)
        if relaxed:
            console.info(f"Relaxed {len(relaxed)} [locked] pins to base floors")
        if relaxed and not self.ctx.dry_run:
            PYPROJECT_PATH.write_text(relaxed_text)

        self.ctx.run("uv lock --upgrade")

        lock_map = parse_lock_versions(UV_LOCK_PATH.read_text())
        new_text, _changes = rewrite_locked_pins(lock_map, PYPROJECT_PATH.read_text())
        before = locked_pin_specs(original_text)
        after = locked_pin_specs(new_text)
        for name in sorted(after):
            if before.get(name) != after[name]:
                console.info(f"[locked] {name}: {before.get(name)} -> {after[name]}")
        if new_text == PYPROJECT_PATH.read_text():
            return
        if self.ctx.dry_run:
            console.info(f"Would update {PYPROJECT_PATH} (dry run)")
            return
        PYPROJECT_PATH.write_text(new_text)
        console.success(f"Updated {PYPROJECT_PATH}")

    def lint(self) -> None:
        super().lint()
        self._guard_locked_pins()

    def _guard_locked_pins(self) -> None:
        lock_map = parse_lock_versions(UV_LOCK_PATH.read_text())
        violations = guard_invariants(lock_map, PYPROJECT_PATH.read_text())
        if not violations:
            console.success("[locked] pins consistent with base floors and uv.lock")
            return
        for violation in violations:
            console.error(violation)
        raise typer.Exit(1)

    def _example_tasks(self, bake_command: str) -> list[CliTask]:
        examples_dir = Path("examples")
        if not examples_dir.exists():
            return []
        return [
            CliTask(
                name=example_dir.name,
                command=["bake", *bake_command.split()],
                cwd=example_dir,
                env=spawn_env(example_dir, prepend_venv=True),
                echo=True,
            )
            for example_dir in sorted(examples_dir.iterdir())
            if example_dir.is_dir()
        ]

    def _update_examples(self) -> None:
        ParallelCliTaskRunner(
            self._example_tasks("update -ff"),
            dry_run=self.ctx.dry_run,
            show_count=True,
            show_summary=False,
        ).run()

    def _update_hooks(self) -> None:
        hooks_dir = Path(".claude/hooks")
        console.start(f"Updating {hooks_dir}")
        self.ctx.run("bun update", cwd=hooks_dir)

    @command()
    def uvx_install_bake_local(
        self,
        editable: Annotated[
            bool, typer.Option("--editable", "-e", help="Install in editable mode")
        ] = False,
    ):
        new_version = zerv.flow(schema="standard-base-prerelease-post-dev", output_format="pep440")
        with self._version_bump_context(new_version):
            editable_flag = "-e " if editable else ""
            self.ctx.run(f"uv tool install {editable_flag}.[lib] --reinstall --force")

    @command()
    def docs(self):
        self.ctx.run("mintlify dev", cwd=Path("docs"))

    @command()
    def docs_check(self):
        self.ctx.run("mintlify broken-links", cwd=Path("docs"))


bakebook = MyBakebook()


@bakebook.command()
def uvx_install_bake():
    bakebook.ctx.run("uv tool install 'bakefile[lib]' --reinstall")


@bakebook.command()
def uvx_install_bake_test():
    bakebook.ctx.run(
        dedent("""\
        uv tool install 'bakefile[lib]' \\
            --index-url https://test.pypi.org/simple/ \\
            --extra-index-url https://pypi.org/simple \\
            --prerelease allow \\
            --reinstall \\
            --index-strategy unsafe-best-match
    """)
    )
