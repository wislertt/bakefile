from bake import command
from bakelib.environ import EnvBakebook
from bakelib.environ.bakebook import E
from bakelib.space.base import BaseSpace


class BaseServiceSpace(EnvBakebook[E], BaseSpace):
    service_name: str

    @command(help="Build the service")
    def build(self):
        self._command_not_available("build")

    @command(help="Deploy the service")
    def deploy(self):
        self._command_not_available("deploy")

    @command(help="Destroy the service")
    def destroy(self):
        self._command_not_available("deploy")
