from typing import Any, Generic, TypeVar

from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

from bake.bakebook.bakebook import Bakebook
from bakelib.environ.base import BaseEnv

E = TypeVar("E", bound=BaseEnv)


class _ExcludeEnvFieldSource(PydanticBaseSettingsSource):
    def __init__(self, source: PydanticBaseSettingsSource, settings_cls: type[BaseSettings]):
        super().__init__(settings_cls)
        self._source: PydanticBaseSettingsSource = source

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        return self._source.get_field_value(field, field_name)

    def __call__(self) -> dict[str, Any]:
        return {k: v for k, v in self._source().items() if k != "env"}


class EnvBakebook(Bakebook, Generic[E]):
    env: E

    def lazy_init(self) -> None:
        """Override for expensive initialization. Called by get_bakebook()."""

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:

        if env_settings is not None:
            env_settings = _ExcludeEnvFieldSource(env_settings, settings_cls)
        if dotenv_settings is not None:
            dotenv_settings = _ExcludeEnvFieldSource(dotenv_settings, settings_cls)
        if file_secret_settings is not None:
            file_secret_settings = _ExcludeEnvFieldSource(file_secret_settings, settings_cls)

        return BaseSettings.settings_customise_sources(
            settings_cls=settings_cls,
            init_settings=init_settings,
            env_settings=env_settings,
            dotenv_settings=dotenv_settings,
            file_secret_settings=file_secret_settings,
        )


class DevEnvBakebook(EnvBakebook[BaseEnv]):
    env: BaseEnv = BaseEnv("dev")


class StagingEnvBakebook(EnvBakebook[BaseEnv]):
    env: BaseEnv = BaseEnv("staging")


class ProdEnvBakebook(EnvBakebook[BaseEnv]):
    env: BaseEnv = BaseEnv("prod")
