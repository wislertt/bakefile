from typing import Annotated

from pydantic import Field, computed_field

from bake.bakebook.bakebook import Bakebook
from bakelib.environ.base import BaseEnv

BaseEnvFieldType = Annotated[BaseEnv, Field(exclude=True, repr=False)]


class EnvBakebook(Bakebook):
    # Field name uses underscore suffix to avoid Pydantic reading from ENV env var
    env_: BaseEnvFieldType = Field(exclude=True, repr=False)

    @computed_field
    @property
    def env(self) -> BaseEnv:
        return self.env_


class DevEnvBakebook(EnvBakebook):
    env_: BaseEnvFieldType = BaseEnv("dev")


class StagingEnvBakebook(EnvBakebook):
    env_: BaseEnvFieldType = BaseEnv("staging")


class ProdEnvBakebook(EnvBakebook):
    env_: BaseEnvFieldType = BaseEnv("prod")
