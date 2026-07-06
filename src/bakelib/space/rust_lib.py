from typing import Annotated

import typer

from bakelib.publisher.crates import CratesPublisher

from .lib import BaseLibSpace
from .params import PublishTokenOption, PublishVersionOption
from .rust import RustSpace


class RustLibSpace(RustSpace, BaseLibSpace):
    def get_publish_registries(self) -> set[str]:
        return set(CratesPublisher.valid_registries)

    def get_publisher(self, registry: str) -> CratesPublisher:
        """Return the Crates publisher instance for the given registry."""
        return CratesPublisher(registry)

    def publish(
        self,
        *,
        registry: Annotated[str, typer.Option(help="Publish registry (crates)")] = "crates",
        token: PublishTokenOption = None,
        version: PublishVersionOption = None,
    ):
        return super().publish(registry=registry, token=token, version=version)
