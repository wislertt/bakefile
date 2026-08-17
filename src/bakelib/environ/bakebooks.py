from typing import Any, Generic, TypeVar, get_args, get_origin

from bakelib.environ.bakebook import EnvBakebook
from bakelib.environ.get import get_bakebook

E = TypeVar("E", bound=EnvBakebook)


def _get_expected_type(cls: type) -> type | None:
    for base in getattr(cls, "__orig_bases__", []):
        if get_origin(base) is EnvBakebooks:
            args = get_args(base)
            if args:
                return args[0]
    return None


class EnvBakebooks(Generic[E]):
    """Groups EnvBakebook instances by environment.

    Parameterize with the common base type of all bakebooks in the group:

        class MyGroup(EnvBakebooks[BaseMyBakebook]):
            dev = DevBakebook()
            prod = ProdBakebook()

        MyGroup.get()   # resolve env, return one bakebook
        MyGroup.all()   # return all bakebooks
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        expected_type = _get_expected_type(cls)
        for attr_name, value in vars(cls).items():
            if isinstance(value, EnvBakebook) and str(value.env) != attr_name:
                raise ValueError(
                    f"Attribute '{attr_name}' has env='{value.env}', expected env='{attr_name}'"
                )
            if (
                expected_type is not None
                and isinstance(value, EnvBakebook)
                and not isinstance(value, expected_type)
            ):
                raise TypeError(
                    f"Attribute '{attr_name}' has type {type(value).__name__}, "
                    f"expected {expected_type.__name__}"
                )

    @classmethod
    def all(cls) -> list[E]:
        return [v for v in vars(cls).values() if isinstance(v, EnvBakebook)]

    @classmethod
    def get(
        cls,
        *,
        env_var_name: str = "ENV",
        env_value: str | None = None,
        fallback_env_value: str | None = None,
        load_dotenv: bool = True,
        lazy_init: bool = True,
    ) -> E:
        return get_bakebook(
            cls.all(),
            env_var_name=env_var_name,
            env_value=env_value,
            fallback_env_value=fallback_env_value,
            load_dotenv=load_dotenv,
            lazy_init=lazy_init,
        )
