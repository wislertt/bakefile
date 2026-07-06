from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar, cast

T = TypeVar("T")


class RefreshNeededError(Exception):
    """Raised when a cached value needs to be refreshed."""


@dataclass(frozen=True)
class FetchFn(ABC, Generic[T]):
    """Abstract base for structured fetch functions.

    Carries the cache ``key`` it fetches for (mirrors ``RefreshableCache.key``).
    Subclasses are frozen dataclasses that add fetch parameters
    and implement __call__ to return the fetched value::

        @dataclass(frozen=True)
        class MyFetch(FetchFn[str]):
            project_id: str
            secret_id: str

            def __call__(self) -> str:
                return fetch_secret(self.project_id, self.secret_id)
    """

    key: str

    @abstractmethod
    def __call__(self) -> T: ...


@dataclass(frozen=True)
class NullFetchFn(FetchFn[T]):
    """FetchFn that always returns None. Use as a no-op fetch placeholder.

    Generic over T: subscript to declare the cached value type so the cache
    can infer it, e.g. ``NullFetchFn[str | None](key)``. The value is always
    None at runtime.
    """

    def __call__(self) -> T:
        return cast(T, None)
