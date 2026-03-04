from typing import Annotated

import typer

from bakelib.publisher.pypi import PyPIPublisher

from .lib import BaseLibSpace
from .python import PythonSpace


class PythonLibSpace(PythonSpace, BaseLibSpace):
    def get_publisher(self, registry: str) -> PyPIPublisher:
        """Return the PyPI publisher instance for the given registry."""
        return PyPIPublisher(self.ctx, registry)

    def publish(
        self,
        *,
        registry: Annotated[
            str, typer.Option(help="Publish registry (test-pypi or pypi)")
        ] = "test-pypi",
        token: Annotated[str | None, typer.Option(help="Publish token")] = None,
        version: Annotated[str | None, typer.Option(help="Version to publish")] = None,
    ):
        return super().publish(registry=registry, token=token, version=version)
