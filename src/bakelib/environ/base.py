from typing import Any, ClassVar

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema


class BaseEnv(str):
    """BaseEnvironment string with comparison and Pydantic support.

    Inherits from str to provide natural string behavior while adding
    comparison operators for priority-based ordering.

    ENV_ORDER is a list where each element is either:
    - A string (normal priority, order matters)
    - A set of strings (equal priority group)

    Example: ["dev", "staging", {"prod", "share"}]
    - "dev" has highest priority (index 0)
    - "staging" has medium priority (index 1)
    - "prod" and "share" have equal lowest priority (both in set at index 2)
    """

    ENV_ORDER: ClassVar[list[str | set[str]]] = ["dev", "staging", "prod"]

    def __init__(self, value: str):
        if not self._is_valid(value):
            raise ValueError(
                f"Invalid {self.__class__.__name__}: '{value}'. "
                f"Must be one of: {self._flattened_env_order()}"
            )

    @classmethod
    def _is_valid(cls, value: str) -> bool:
        try:
            cls._get_priority_index(value)
            return True
        except ValueError:
            return False

    @classmethod
    def _flattened_env_order(cls) -> list[str]:
        result: list[str] = []
        for item in cls.ENV_ORDER:
            if isinstance(item, set):
                result.extend(sorted(item))
            else:
                result.append(item)
        return result

    @classmethod
    def _get_priority_index(cls, value: str) -> int:
        for idx, item in enumerate(cls.ENV_ORDER):
            is_in_set = isinstance(item, set) and value in item
            is_equal = item == value
            if is_in_set or is_equal:
                return idx
        raise ValueError(f"Value '{value}' not found in ENV_ORDER")

    def __lt__(self, other: str) -> bool:
        if type(other) is not type(self):
            return NotImplemented
        self_idx = self._get_priority_index(str(self))
        other_idx = self._get_priority_index(str(other))
        if self_idx != other_idx:
            return self_idx < other_idx
        # Same priority group, use alphabetical as tiebreaker
        return str(self) < str(other)

    def __le__(self, other: str) -> bool:
        if type(other) is not type(self):
            return NotImplemented
        return self < other or self == other

    def __gt__(self, other: str) -> bool:
        if type(other) is not type(self):
            return NotImplemented
        return not (self < other) and self != other

    def __ge__(self, other: str) -> bool:
        if type(other) is not type(self):
            return NotImplemented
        return not (self < other)

    def __eq__(self, other: object) -> bool:
        if type(other) is not type(self):
            return False
        return str(self) == str(other)

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash(str(self))

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
