from typing import Annotated

import typer

from bake import command

from .base import BaseSpace


class SubmodulesUtils(BaseSpace):
    def _sync_submodules(self, frozen: bool = False) -> None:
        remote_flag = "" if frozen else " --remote"
        self.ctx.run(f"git submodule update --init --recursive{remote_flag}")

    @command(help="Sync git submodules")
    def sync_submodules(
        self,
        frozen: Annotated[
            bool,
            typer.Option(
                "--frozen",
                help="Skip --remote flag to keep submodule commits",
            ),
        ] = False,
    ) -> None:
        self._sync_submodules(frozen=frozen)

    def update(self) -> None:
        super().update()
        self._sync_submodules(frozen=False)

    def setup_tools(self) -> None:
        super().setup_tools()
        self._sync_submodules(frozen=True)

    def _assert_tools(self) -> None:
        super()._assert_tools()
        self._sync_submodules(frozen=True)
