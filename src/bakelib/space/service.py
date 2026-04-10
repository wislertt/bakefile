import typer

from bake import Bakebook, command, console
from bakelib.space.base import BaseSpace


class ServiceSpaceMixin(Bakebook):
    service_name: str | None = None

    def _command_not_available(self, command_name: str) -> None:
        console.error(f"Command '{command_name}' is not available")
        raise typer.Exit(1)

    @command(help="Build the service")
    def build(self) -> None:
        self._command_not_available("build")

    @command(help="Deploy the service")
    def deploy(self):
        self._command_not_available("deploy")

    @command(help="Verify deployment succeeded and is healthy")
    def assert_deploy(self):
        self._command_not_available("assert-deploy")

    @command(help="Destroy the service")
    def destroy(self):
        self._command_not_available("destroy")

    @command(help="Build and deploy the service")
    def bd(self):
        console.cmd("bake build")
        self.build()
        console.cmd("bake deploy")
        self.deploy()


class BaseServiceSpace(ServiceSpaceMixin, BaseSpace): ...
