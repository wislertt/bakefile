from bakelib.environ import BaseEnv, EnvBakebook
from bakelib.environ.bakebook import DevEnvMixin, ProdEnvMixin, StagingEnvMixin


class DevEnvBB(DevEnvMixin, EnvBakebook[BaseEnv]):
    pass


class StagingEnvBB(StagingEnvMixin, EnvBakebook[BaseEnv]):
    pass


class ProdEnvBB(ProdEnvMixin, EnvBakebook[BaseEnv]):
    pass
