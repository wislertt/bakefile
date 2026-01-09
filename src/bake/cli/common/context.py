import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Literal, overload

import click
import typer
from typer.core import TyperCommand

from bake.ui.run import run as _run
from bake.ui.run.script import run_script as _run_script

from .obj import BakefileObject

if TYPE_CHECKING:
    from bake.bakebook.bakebook import Bakebook


class Context(typer.Context):
    obj: BakefileObject

    @property
    def dry_run(self) -> bool:
        return self.obj.dry_run

    @property
    def verbosity(self) -> int:
        return self.obj.verbosity

    @property
    def bakebook(self) -> "Bakebook | None":
        return self.obj.bakebook

    @overload
    def run(
        self,
        cmd: str,
        *,
        capture_output: Literal[True] = True,
        check: bool = True,
        cwd: Path | str | None = None,
        stream: bool = True,
        shell: bool | None = None,
        echo: bool = True,
        **kwargs,
    ) -> subprocess.CompletedProcess[str]: ...

    @overload
    def run(
        self,
        cmd: str,
        *,
        capture_output: Literal[False],
        check: bool = True,
        cwd: Path | str | None = None,
        stream: bool = True,
        shell: bool | None = None,
        echo: bool = True,
        **kwargs,
    ) -> subprocess.CompletedProcess[None]: ...

    @overload
    def run(
        self,
        cmd: list[str] | tuple[str, ...],
        *,
        capture_output: Literal[True] = True,
        check: bool = True,
        cwd: Path | str | None = None,
        stream: bool = True,
        shell: bool | None = None,
        echo: bool = True,
        **kwargs,
    ) -> subprocess.CompletedProcess[str]: ...

    @overload
    def run(
        self,
        cmd: list[str] | tuple[str, ...],
        *,
        capture_output: Literal[False],
        check: bool = True,
        cwd: Path | str | None = None,
        stream: bool = True,
        shell: bool | None = None,
        echo: bool = True,
        **kwargs,
    ) -> subprocess.CompletedProcess[None]: ...

    def run(
        self,
        cmd: str | list[str] | tuple[str, ...],
        *,
        capture_output: bool = True,
        check: bool = True,
        cwd: Path | str | None = None,
        stream: bool = True,
        shell: bool | None = None,
        echo: bool = True,
        **kwargs,
    ) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[None]:
        return _run(
            cmd,
            capture_output=capture_output,
            check=check,
            cwd=cwd,
            stream=stream,
            shell=shell,
            echo=echo,
            dry_run=self.obj.dry_run,
            **kwargs,
        )

    def run_script(
        self,
        title: str,
        script: str,
        *,
        capture_output: bool = True,
        check: bool = True,
        cwd: Path | str | None = None,
        stream: bool = True,
        echo: bool = True,
        **kwargs,
    ) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[None]:
        return _run_script(
            title,
            script,
            capture_output=capture_output,
            check=check,
            cwd=cwd,
            stream=stream,
            echo=echo,
            dry_run=self.obj.dry_run,
            **kwargs,
        )


class BakeCommand(TyperCommand):
    context_class: type[click.Context] = Context
