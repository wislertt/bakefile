from bake import command, console
from bakelib.space.base import BaseSpace


class BaseServiceSpace(BaseSpace):
    service_name: str

    @command(help="Build the service")
    def build(self) -> None:
        self._command_not_available("build")

    @command(help="Deploy the service")
    def deploy(self):
        self._command_not_available("deploy")

    @command(help="Destroy the service")
    def destroy(self):
        self._command_not_available("destroy")

    @command(help="Build and deploy the service")
    def bd(self):
        console.cmd("bake build")
        self.build()
        console.cmd("bake deploy")
        self.deploy()
