import contextlib
import functools
import inspect
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar, Generic, ParamSpec, TypeVar

import keyring as kr
from keyring.errors import PasswordDeleteError
from pydantic import BaseModel, TypeAdapter
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_none

from bakelib.refreshable_cache.exceptions import RefreshNeededError

if TYPE_CHECKING:
    from tenacity.stop import StopBaseT
    from tenacity.wait import WaitBaseT


logger = logging.getLogger(__name__)

P = ParamSpec("P")
F = TypeVar("F", bound=Callable[..., Any])
T = TypeVar("T")
CachedT = TypeVar("CachedT", covariant=True)


class CacheEntry(BaseModel, Generic[CachedT]):
    """Cache entry containing the cached value and timestamp."""

    value: CachedT
    timestamp: float


DEFAULT_NAMESPACE = "bakelib.refreshable_cache"


class RefreshableCache(ABC, Generic[CachedT]):
    """Cache that can be refreshed when values expire or become invalid."""

    RefreshNeededError: type[RefreshNeededError] = RefreshNeededError

    def __init__(
        self,
        key: str,
        fetch_fn: Callable[[], CachedT],
        ttl: float | None = None,
        namespace: str | None = None,
        stop: "StopBaseT | None" = None,
        wait: "WaitBaseT | None" = None,
        cached_type: Any = None,
    ) -> None:
        self._key = key
        self._fetch_fn = fetch_fn
        self._ttl = ttl
        self._namespace = namespace if namespace is not None else DEFAULT_NAMESPACE
        self._stop = stop if stop is not None else stop_after_attempt(2)
        self._wait = wait if wait is not None else wait_none()

        # Determine cached type: explicit cached_type or infer from fetch_fn
        if cached_type is not None:
            return_type = cached_type
        else:
            return_type = inspect.signature(fetch_fn).return_annotation
            if return_type is inspect.Parameter.empty:
                msg = "fetch_fn must have a return type annotation or cached_type must be provided"
                raise TypeError(msg)

        self._adapter = TypeAdapter(CacheEntry[return_type])

    def _get_full_key(self) -> str:
        return f"{self._namespace}:{self._key}"

    def _serialize_entry(self, value: CachedT) -> bytes:
        entry = CacheEntry(value=value, timestamp=time.time())
        return self._adapter.dump_json(entry)

    def _deserialize_entry(self, data: bytes) -> CacheEntry[CachedT]:
        return self._adapter.validate_json(data)

    def _is_expired(self, timestamp: float) -> bool:
        if self._ttl is None:
            return False
        return time.time() - timestamp > self._ttl

    def get_value(self) -> CachedT:
        cached = self._get_entry()
        if cached is None:
            logger.debug(f"Cache miss for key '{self._key}', fetching value")
            return self._refresh()
        if self._is_expired(cached.timestamp):
            logger.debug(f"Cache expired for key '{self._key}', fetching fresh value")
            return self._refresh()
        logger.debug(f"Cache hit for key '{self._key}'")
        return cached.value

    def _refresh(self) -> CachedT:
        logger.debug(f"Refreshing value for key '{self._key}'")
        value = self._fetch_fn()
        self.set(value)
        return value

    def catch_refresh(self, func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        @retry(
            stop=self._stop,
            wait=self._wait,
            retry=retry_if_exception_type(self.RefreshNeededError),
            reraise=True,
        )
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except self.RefreshNeededError:
                self.delete()
                raise

        return wrapper

    @abstractmethod
    def _get_entry(self) -> CacheEntry[CachedT] | None: ...

    @abstractmethod
    def set(self, value: CachedT) -> None: ...

    @abstractmethod
    def delete(self) -> None: ...


class KeyringCache(RefreshableCache[CachedT]):
    """Cache using system keyring for persistent storage."""

    def _get_entry(self) -> CacheEntry[CachedT] | None:
        data = kr.get_password(self._namespace, self._key)
        if data is None:
            return None
        return self._deserialize_entry(data.encode())

    def set(self, value: CachedT) -> None:
        data = self._serialize_entry(value).decode()
        kr.set_password(self._namespace, self._key, data)

    def delete(self) -> None:
        with contextlib.suppress(PasswordDeleteError):
            kr.delete_password(self._namespace, self._key)


class MemoryCache(RefreshableCache[CachedT]):
    """In-memory cache for ephemeral storage."""

    _storage: ClassVar[dict[str, CacheEntry[CachedT]]] = {}

    def _get_entry(self) -> CacheEntry[CachedT] | None:
        entry = self._storage.get(self._get_full_key())
        if entry is None:
            return None
        return entry

    def set(self, value: CachedT) -> None:
        self._storage[self._get_full_key()] = CacheEntry(value=value, timestamp=time.time())

    def delete(self) -> None:
        self._storage.pop(self._get_full_key(), None)


class NullCache(RefreshableCache[CachedT]):
    """Cache that doesn't cache anything (Null Object pattern).

    Useful as a final fallback when you want to explicitly disable caching.
    Reads always return None (triggering fetch), writes/deletes do nothing.
    """

    def _get_entry(self) -> CacheEntry[CachedT] | None:
        return None

    def set(self, value: CachedT) -> None:
        pass

    def delete(self) -> None:
        pass


class ChainedCache(RefreshableCache[CachedT]):
    """Tries multiple backends in order.

    Reads from the first backend that has data.
    Writes to all backends (stops on first success).
    """

    _backends: list[RefreshableCache[CachedT]]

    def __init__(
        self,
        backends: list[type[RefreshableCache[CachedT]]],
        key: str,
        fetch_fn: Callable[[], CachedT],
        ttl: float | None = None,
        namespace: str | None = None,
        stop: "StopBaseT | None" = None,
        wait: "WaitBaseT | None" = None,
        cached_type: Any = None,
    ) -> None:
        super().__init__(
            key=key,
            fetch_fn=fetch_fn,
            ttl=ttl,
            namespace=namespace,
            stop=stop,
            wait=wait,
            cached_type=cached_type,
        )
        self._backends = [
            backend(
                key=key,
                fetch_fn=fetch_fn,
                ttl=ttl,
                namespace=namespace,
                stop=stop,
                wait=wait,
                cached_type=cached_type,
            )
            for backend in backends
        ]

    def _get_entry(self) -> CacheEntry[CachedT] | None:
        for backend in self._backends:
            try:
                entry = backend._get_entry()
                if entry is not None:
                    return entry
            except Exception:
                continue
        return None

    def set(self, value: CachedT) -> None:
        for backend in self._backends:
            try:
                backend.set(value)
                return
            except Exception:
                continue

    def delete(self) -> None:
        for backend in self._backends:
            try:
                backend.delete()
            except Exception:
                continue
