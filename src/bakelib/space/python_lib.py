from typing import Annotated

import typer

from bakelib.publisher.pypi import PyPIPublisher

from .lib import BaseLibSpace
from .params import PublishTokenOption, PublishVersionOption
from .python import PythonSpace


class PythonLibSpace(PythonSpace, BaseLibSpace):
    def get_publish_registries(self) -> set[str]:
        return set(PyPIPublisher.valid_registries)

    def get_publisher(self, registry: str) -> PyPIPublisher:
        """Return the PyPI publisher instance for the given registry."""
        return PyPIPublisher(self.ctx, registry)

    def publish(
        self,
        *,
        registry: Annotated[
            str, typer.Option(help="Publish registry (test-pypi or pypi)")
        ] = "test-pypi",
        token: PublishTokenOption = None,
        version: PublishVersionOption = None,
    ):
        return super().publish(registry=registry, token=token, version=version)
