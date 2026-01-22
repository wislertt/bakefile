import os
from typing import TypeVar

from dotenv import load_dotenv as _load_dotenv

from .bakebook import EnvBakebook

# TODO: When min Python >= 3.12, use PEP 695 type parameter syntax:
# def get_bakebook[E: EnvBakebook](bakebooks: list[E], ...) -> E:
E = TypeVar("E", bound=EnvBakebook)


def get_bakebook(
    bakebooks: list[E],
    *,
    env_var_name: str = "ENV",
    env_value: str | None = None,
    load_dotenv: bool = True,
) -> E:
    if not bakebooks:
        raise ValueError("bakebooks list cannot be empty")

    # Convert to dict for O(1) lookup and duplicate detection
    bakebooks_by_env: dict[str, E] = {}
    for bb in bakebooks:
        if not hasattr(bb, "env") or bb.env is None:
            raise ValueError(f"All bakebooks must have an 'env' attribute. Found: {bb}")
        env = str(bb.env)
        if env in bakebooks_by_env:
            raise ValueError(f"Duplicate env '{env}' found in bakebooks list")
        bakebooks_by_env[env] = bb

    # Get environment value
    if env_value is None:
        if load_dotenv:
            _load_dotenv()
        env_value = os.getenv(env_var_name)

    # Env var not set - return lowest priority (min)
    if env_value is None or env_value == "":
        return bakebooks_by_env[str(min(bb.env for bb in bakebooks))]
    # If env var is set, require exact match
    elif env_value in bakebooks_by_env:
        return bakebooks_by_env[env_value]

    raise ValueError(
        f"No bakebook found with env='{env_value}'. "
        f"Available envs: {sorted(bakebooks_by_env.keys())}"
    )
