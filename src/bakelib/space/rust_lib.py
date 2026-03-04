from typing import Annotated

import typer

from bakelib.publisher.crates import CratesPublisher

from .lib import BaseLibSpace
from .rust import RustSpace


class RustLibSpace(RustSpace, BaseLibSpace):
    def get_publisher(self, registry: str) -> CratesPublisher:
        """Return the Crates publisher instance for the given registry."""
        return CratesPublisher(self.ctx, registry)

    def publish(
        self,
        *,
        registry: Annotated[str, typer.Option(help="Publish registry (crates)")] = "crates",
        token: Annotated[str | None, typer.Option(help="Publish token")] = None,
        version: Annotated[str | None, typer.Option(help="Version to publish")] = None,
    ):
        return super().publish(registry=registry, token=token, version=version)
