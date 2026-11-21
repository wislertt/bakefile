import sys
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar, cast

import typer

from bake.ui import console

T = TypeVar("T")


class RefreshNeededError(Exception):
    """Raised when a cached value needs to be refreshed."""


# raised by a fetch fn whose source gave no new value; refresh keeps the cached one
class FetchDeclinedError(Exception):
    pass


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


@dataclass(frozen=True)
class CallableFetchFn(FetchFn[T]):
    """FetchFn that delegates to an arbitrary callable.

    Generic over T: subscript to declare the cached value type, e.g.
    ``CallableFetchFn[str | None](key, fetch=some_callable)``. The callable is
    invoked (no args) on every cache fill.
    """

    fetch: Callable[[], T]

    def __call__(self) -> T:
        return self.fetch()


def can_prompt() -> bool:
    return sys.stdin.isatty()


@dataclass(frozen=True)
class UserInputFetchFn(FetchFn[str]):
    """FetchFn whose source is the user typing the value (hidden input).

    Empty input or no terminal declines, so refresh keeps the stored value.
    ``label`` defaults to the ``key``.
    """

    label: str | None = None

    def _no_terminal_hint(self) -> str:
        return "run this command in an interactive terminal to set it"

    def __call__(self) -> str:
        label = self.label or self.key
        if not can_prompt():
            console.warning(
                f"{self.key} needs a terminal to prompt for {label}; {self._no_terminal_hint()}"
            )
            raise FetchDeclinedError(self.key)
        value = typer.prompt(
            f"Paste your {label} (empty to skip)",
            default="",
            show_default=False,
            hide_input=True,
        )
        if not value:
            raise FetchDeclinedError(self.key)
        return value
