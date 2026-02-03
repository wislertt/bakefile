from pathlib import Path
from typing import Annotated

import typer

from bake import Context, command, console
from bakelib import PythonLibSpace


class MyBakebook(PythonLibSpace):
    def update(self, ctx: Context) -> None:
        super().update(ctx)
        self._update_examples(ctx)
        self._update_hooks(ctx)

    def _update_examples(self, ctx: Context) -> None:
        examples_dir = Path("examples")
        if not examples_dir.exists():
            return

        for example_dir in sorted(examples_dir.iterdir()):
            if not example_dir.is_dir():
                continue
            console.start(f"Updating {example_dir}")
            ctx.run("bake update", cwd=example_dir)

    def _update_hooks(self, ctx: Context) -> None:
        hooks_dir = Path(".claude/hooks")
        console.start(f"Updating {hooks_dir}")
        ctx.run("npm update", cwd=hooks_dir)

    @command()
    def uvx_install_bake_local(
        self,
        ctx: Context,
        editable: Annotated[
            bool, typer.Option("--editable", "-e", help="Install in editable mode")
        ] = False,
    ):
        new_version = self.zerv_versioning(ctx)
        with self._version_bump_context(ctx, new_version):
            editable_flag = "-e " if editable else ""
            ctx.run(f"uv tool install {editable_flag}.[lib] --reinstall --force")


bakebook = MyBakebook()


@bakebook.command()
def uvx_install_bake(ctx: Context):
    ctx.run("uv tool install 'bakefile[lib]' --reinstall")


@bakebook.command()
def uvx_install_bake_test(ctx: Context):
    ctx.run(
        "uv tool install bakefile[lib] "
        "--index-url https://test.pypi.org/simple/ "
        "--extra-index-url https://pypi.org/simple "
        "--prerelease allow "
        "--reinstall "
        "--index-strategy unsafe-best-match"
    )
