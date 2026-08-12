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

logger = logging.getLogger(__name__)


class MyBakebook(GitHubActionsTools, PythonLibSpace):
    bake_log: str = DEFAULT_BAKE_LOG
    bake_log_verbosity: params.BakeLogVerbosityField = 3
    bake_log_pretty: bool = DEFAULT_BAKE_LOG_PRETTY

    def _get_mise_tools(self) -> set[str]:
        mise_tools = super()._get_mise_tools()
        mise_tools.remove("pipx:bakefile")
        return mise_tools

    def _update_project(self) -> None:
        super()._update_project()
        self._update_examples()
        self._update_hooks()

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
