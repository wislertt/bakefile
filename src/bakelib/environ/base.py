import functools
from typing import Any, ClassVar

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

EnvPriorityOrderType = tuple[str | frozenset[str], ...]


class _FrozenEnvMeta(type):
    """Metaclass that prevents mutation of CAPS class variables at class level.

    Protects all-uppercase class variables (Python convention for constants)
    from being reassigned after class definition.
    """

    def __setattr__(cls, name: str, value: Any) -> None:
        # Protect all-uppercase attributes (convention for constants)
        if name.isupper() and hasattr(cls, name):
            raise AttributeError(
                f"Cannot mutate {cls.__name__}.{name}. It is frozen and cannot be reassigned."
            )
        super().__setattr__(name, value)


class _BaseEnv(str, metaclass=_FrozenEnvMeta):
    """Base infrastructure - handles __init_subclass__ wrapping and __setattr__ protection.

    This class provides the foundation for immutable environment classes:
    - Automatic _initialized flag via __init_subclass__ wrapping
    - Instance-level attribute freezing via __setattr__
    - All subclasses get frozen behavior automatically
    """

    ENV_PRIORITY_ORDER: ClassVar[EnvPriorityOrderType] = ("dev", "staging", "prod")
    _initialized: bool = False

    def __init_subclass__(cls) -> None:
        """Wrap subclass __init__ to automatically set _initialized = True.

        This ensures that ALL subclasses (including BaseEnv itself when defined)
        get the wrapping behavior without manual _initialized = True calls.
        """
        # Avoid double-wrapping if __init__ is already wrapped (inherited from parent)
        if cls.__init__.__name__ == "wrapped_init":
            return

        original_init = cls.__init__

        def wrapped_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            object.__setattr__(self, "_initialized", True)

        cls.__init__ = wrapped_init

    def __setattr__(self, name: str, value: Any) -> None:
        """Protect "_" attributes that have already been set.

        Once _initialized is True:
        - Setting new "_" attributes is allowed
        - Re-setting existing "_" attributes is blocked
        """
        if name.startswith("_") and self._initialized and hasattr(self, name):
            raise AttributeError(
                f"Cannot mutate {self.__class__.__name__}.{name}. "
                "It is frozen and cannot be reassigned."
            )
        super().__setattr__(name, value)


class BaseEnv(_BaseEnv):
    """BaseEnvironment string with priority-based ordering.

    Inherits from str to provide natural string behavior while adding
    comparison operators for priority-based ordering.

    COMPARISON SEMANTICS:
        - Ordering (<, <=, >, >=) is by INDEX (lower index = "less than")
        - Equality (==) is by INDEX (same index = equal)
        - UNHASHABLE - use str(env) for dict keys/sets

    ENV_PRIORITY_ORDER is a tuple where each element is either:
    - A string (normal priority, order matters)
    - A frozenset of strings (equal priority group)

    Example: ("dev", "staging", frozenset({"prod", "share"}))
    - "dev" has lowest index (index 0), applied first
    - "staging" has medium index (index 1)
    - "prod" and "share" have equal highest index (index 2), applied last

    For comparison: lower index = "less than" (applies earlier in pipeline)

    Example comparison behavior:
        dev = BaseEnv("dev")
        prod = BaseEnv("prod")
        prod2 = BaseEnv("prod")

        dev < prod          # True (dev has lower index: 0 < 2)
        prod == prod2      # True (same index: 2 == 2)
        str(prod) == str(prod2)  # True (same string value)

    For collections, convert to string first:
        envs = {str(dev), str(prod)}  # ✅ Works
        env_map = {str(dev): "value"}  # ✅ Works
        envs = {dev, prod}  # ❌ TypeError: unhashable
    """

    ENV_PRIORITY_ORDER: ClassVar[EnvPriorityOrderType] = ("dev", "staging", "prod")

    @classmethod
    @functools.cache
    def _compute_flattened_envs(cls) -> tuple[str, ...]:
        result: list[str] = []
        for item in cls.ENV_PRIORITY_ORDER:
            if isinstance(item, frozenset):
                result.extend(sorted(item))
            else:
                result.append(item)
        return tuple(result)

    @property
    def flattened_envs(self) -> tuple[str, ...]:
        """Flattened list of all valid environment codes (computed and cached)."""
        return self._compute_flattened_envs()

    def __init__(self, value: str):
        self._get_priority_index(value)

    def _get_priority_index(self, value: str) -> int:
        for idx, item in enumerate(self.ENV_PRIORITY_ORDER):
            is_in_set = isinstance(item, frozenset) and value in item
            is_equal = item == value
            if is_in_set or is_equal:
                return idx
        raise ValueError(
            f"Value '{value}' not found in ENV_PRIORITY_ORDER. Must be one of: "
            f"{self.flattened_envs}"
        )

    def _get_comparison_key(self) -> tuple:
        """Get comparison key for this environment. Default: by priority index."""
        return (self._get_priority_index(str(self)),)

    def __lt__(self, other: str) -> bool:
        if type(other) is not type(self):
            return NotImplemented
        return self._get_comparison_key() < other._get_comparison_key()

    def __le__(self, other: str) -> bool:
        if type(other) is not type(self):
            return NotImplemented
        return self._get_comparison_key() <= other._get_comparison_key()

    def __gt__(self, other: str) -> bool:
        if type(other) is not type(self):
            return NotImplemented
        return self._get_comparison_key() > other._get_comparison_key()

    def __ge__(self, other: str) -> bool:
        if type(other) is not type(self):
            return NotImplemented
        return self._get_comparison_key() >= other._get_comparison_key()

    def __eq__(self, other: object) -> bool:
        if type(other) is not type(self):
            return False
        return self._get_comparison_key() == other._get_comparison_key()

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    __hash__ = None  # Unhashable - use str(env) for dict keys

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self!s}')"

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        """Pydantic v2 integration for custom type validation."""
        return core_schema.no_info_after_validator_function(cls, handler(str))

    @classmethod
    def validate(cls, v: object) -> "BaseEnv":
        """Validate and convert input to BaseEnv."""
        if isinstance(v, cls):
            return v
        if isinstance(v, str):
            return cls(v)
        raise ValueError(f"Cannot convert {type(v).__name__} to {cls.__name__}")


class BaseSubEnv(BaseEnv):
    """Base environment with sub-environment support (dev1, staging2, prod3, etc.).

    Inherits ENV_PRIORITY_ORDER from BaseEnv: ("dev", "staging", "prod").

    Comparison: main env (by priority index), then sub-number (dev < dev1 < dev2).
    Subclasses may override ENV_PRIORITY_ORDER for different main env codes.
    """

    _main: str
    _sub: int | None

    def __init__(self, value: str):
        self._validate_env_priority_order()
        self._parse_env_code(value)
        self._get_priority_index(self.main)

    @property
    def main(self) -> str:
        return self._main

    @property
    def sub(self) -> int | None:
        return self._sub

    def _parse_env_code(self, code: str) -> None:
        """Parse environment code and set self._main and self._sub.

        Sets ("dev", None) for "dev", or ("dev", 1) for "dev1".
        Raises ValueError for invalid codes.
        """
        # Sort by length descending to match multi-char codes before single-char
        flat_envs = self.flattened_envs
        main_codes = sorted(flat_envs, key=len, reverse=True)

        for main in main_codes:
            if code == main:
                self._main = main
                self._sub = None
                return
            if not code.startswith(main):
                continue

            suffix = code[len(main) :]
            if not suffix.isdigit():
                continue

            sub = int(suffix)
            if sub <= 0:
                continue

            self._main = main
            self._sub = sub
            return

        raise ValueError(
            f"Invalid {self.__class__.__name__}: '{code}'. "
            f"Must be one of: {flat_envs}, "
            f"optionally with a positive numeric suffix (e.g., {flat_envs[0]}1, {flat_envs[0]}2)."
        )

    def _validate_env_priority_order(self) -> None:
        for code in self.flattened_envs:
            if not code[-1].isdigit():
                continue
            raise ValueError(
                f"Main env code '{code}' cannot end with a digit "
                f"(conflicts with sub-env syntax like {self.flattened_envs[0]}1)"
            )

    def _get_comparison_key(self) -> tuple:
        """Compare by (main_priority_index, -sub_number).

        Lower index = applies earlier (dev < staging < prod).
        Higher sub = applies earlier (dev5 < dev1 < dev).
        """
        main_idx = self._get_priority_index(self.main)
        sub_key = 0 if self.sub is None else -self.sub
        return (main_idx, sub_key)
