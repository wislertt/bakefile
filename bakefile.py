from pathlib import Path
from typing import Annotated

import typer
import zerv

from bake import command, console
from bakelib import PythonLibSpace


class MyBakebook(PythonLibSpace):
    def update(self) -> None:
        super().update()
        self._update_examples()
        self._update_hooks()

    def _update_examples(self) -> None:
        examples_dir = Path("examples")
        if not examples_dir.exists():
            return

        for example_dir in sorted(examples_dir.iterdir()):
            if not example_dir.is_dir():
                continue
            console.start(f"Updating {example_dir}")
            self.ctx.run("bake update", cwd=example_dir)

    def _update_hooks(self) -> None:
        hooks_dir = Path(".claude/hooks")
        console.start(f"Updating {hooks_dir}")
        self.ctx.run("npm update", cwd=hooks_dir)

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
        "uv tool install bakefile[lib] "
        "--index-url https://test.pypi.org/simple/ "
        "--extra-index-url https://pypi.org/simple "
        "--prerelease allow "
        "--reinstall "
        "--index-strategy unsafe-best-match"
    )
