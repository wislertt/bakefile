import os
from typing import TypeVar

from dotenv import load_dotenv as _load_dotenv

from .bakebook import EnvBakebook

E = TypeVar("E", bound=EnvBakebook)


def _build_bakebook_dict(bakebooks: list[E]) -> dict[str, E]:
    if not bakebooks:
        raise ValueError("bakebooks list cannot be empty")

    bakebooks_by_env: dict[str, E] = {}
    for bb in bakebooks:
        if not hasattr(bb, "env") or bb.env is None:
            raise ValueError(f"All bakebooks must have an 'env' attribute. Found: {bb}")
        env = str(bb.env)
        if env in bakebooks_by_env:
            raise ValueError(f"Duplicate env '{env}' found in bakebooks list")
        bakebooks_by_env[env] = bb

    return bakebooks_by_env


def _resolve_env_value(
    env_var_name: str,
    env_value: str | None,
    fallback_env_value: str | None,
    load_dotenv: bool,
) -> str | None:
    if env_value is None:
        if load_dotenv:
            _load_dotenv()
        env_value = os.getenv(env_var_name)
    return env_value or fallback_env_value


def _select_bakebook(bakebooks_by_env: dict[str, E], env_value: str | None) -> E:
    if env_value is None or env_value == "":
        return bakebooks_by_env[str(min(bb.env for bb in bakebooks_by_env.values()))]
    elif env_value in bakebooks_by_env:
        return bakebooks_by_env[env_value]
    else:
        raise ValueError(
            f"No bakebook found with env='{env_value}'. "
            f"Available envs: {sorted(bakebooks_by_env.keys())}"
        )


def get_bakebook(
    bakebooks: list[E],
    *,
    env_var_name: str = "ENV",
    env_value: str | None = None,
    fallback_env_value: str | None = None,
    load_dotenv: bool = True,
    lazy_init: bool = True,
) -> E:
    bakebooks_by_env = _build_bakebook_dict(bakebooks=bakebooks)
    env_value = _resolve_env_value(
        env_var_name=env_var_name,
        env_value=env_value,
        fallback_env_value=fallback_env_value,
        load_dotenv=load_dotenv,
    )
    selected = _select_bakebook(bakebooks_by_env=bakebooks_by_env, env_value=env_value)

    if lazy_init:
        selected.lazy_init()

    return selected
