from typing import Any, Generic, TypeVar

from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

from bake.bakebook.bakebook import Bakebook, BakebookMixin
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


def _get_expected_env_type(cls: type) -> type | None:
    for base in cls.__bases__:
        metadata = getattr(base, "__pydantic_generic_metadata__", None)
        if metadata is not None and metadata.get("origin") is EnvBakebook:
            args = metadata.get("args", ())
            if args:
                return args[0]
    return None


class EnvBakebook(Bakebook, Generic[E]):
    env: E

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        expected_env_type = _get_expected_env_type(cls)
        if expected_env_type is None:
            return

        env_annotation = cls.__annotations__.get("env")
        if env_annotation is not None and not issubclass(env_annotation, expected_env_type):
            raise TypeError(
                f"'{cls.__name__}.env' annotation is "
                f"{env_annotation.__name__}, "
                f"expected {expected_env_type.__name__}"
            )

    def lazy_init(self) -> None:
        """Override for expensive initialization. Called by get_bakebook()."""
        self.setup_logging()

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


class DevEnvMixin(BakebookMixin):
    env: BaseEnv = BaseEnv("dev")


class StagingEnvMixin(BakebookMixin):
    env: BaseEnv = BaseEnv("staging")


class ProdEnvMixin(BakebookMixin):
    env: BaseEnv = BaseEnv("prod")
