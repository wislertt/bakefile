import functools
import inspect
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Coroutine
from typing import TYPE_CHECKING, Any, ClassVar, Generic, ParamSpec, TypeVar

import keyring as kr
from keyring.errors import PasswordDeleteError
from pydantic import BaseModel, TypeAdapter
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_none

from bakelib.refreshable_cache.utils import FetchFn, RefreshNeededError

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
        fetch_fn: "Callable[[], CachedT] | FetchFn[CachedT]",
        ttl: float | None = None,
        namespace: str | None = None,
        stop: "StopBaseT | None" = None,
        wait: "WaitBaseT | None" = None,
        cached_type: Any = None,
    ) -> None:
        if isinstance(fetch_fn, FetchFn) and fetch_fn.key != key:
            raise ValueError(f"fetch_fn.key '{fetch_fn.key}' does not match key '{key}'")
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
            return self._fetch()
        if self._is_expired(cached.timestamp):
            logger.debug(f"Cache expired for key '{self._key}', fetching fresh value")
            return self._fetch()
        value = cached.value
        type_name = type(value).__name__
        detail = f", len={len(value)}" if isinstance(value, str) else ""
        logger.debug(f"Cache hit for key '{self._key}' (type={type_name}{detail})")
        return value

    def has_value(self) -> bool:
        return self._get_entry() is not None

    def _fetch(self) -> CachedT:
        """Fetch value from source and cache it."""
        logger.debug(f"Fetching value for key '{self._key}'")
        value = self._fetch_fn()
        self.set(value)
        return value

    def refresh(self) -> CachedT:
        """Force refresh: clear cache and fetch fresh value."""
        self.delete()
        return self._fetch()

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

    def acatch_refresh(
        self, func: Callable[P, Awaitable[T]]
    ) -> Callable[P, Coroutine[Any, Any, T]]:
        @functools.wraps(func)
        @retry(
            stop=self._stop,
            wait=self._wait,
            retry=retry_if_exception_type(self.RefreshNeededError),
            reraise=True,
        )
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return await func(*args, **kwargs)
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
        logger.debug(
            f"KeyringCache: getting entry for namespace='{self._namespace}', key='{self._key}'"
        )
        data = kr.get_password(self._namespace, self._key)
        if data is None:
            logger.debug(
                f"KeyringCache: cache miss for namespace='{self._namespace}', key='{self._key}'"
            )
            return None
        logger.debug(
            f"KeyringCache: cache hit for namespace='{self._namespace}', key='{self._key}'"
        )
        return self._deserialize_entry(data.encode())

    def set(self, value: CachedT) -> None:
        logger.debug(
            f"KeyringCache: setting entry for namespace='{self._namespace}', key='{self._key}'"
        )
        data = self._serialize_entry(value).decode()
        kr.set_password(self._namespace, self._key, data)
        logger.debug(
            f"KeyringCache: successfully set entry for "
            f"namespace='{self._namespace}', key='{self._key}'"
        )

    def delete(self) -> None:
        logger.debug(
            f"KeyringCache: deleting entry for namespace='{self._namespace}', key='{self._key}'"
        )
        try:
            kr.delete_password(self._namespace, self._key)
            logger.debug(
                "KeyringCache: successfully deleted entry for "
                f"namespace='{self._namespace}', key='{self._key}'"
            )
        except PasswordDeleteError:
            logger.debug(
                "KeyringCache: entry not found for deletion "
                f"(namespace='{self._namespace}', key='{self._key}')"
            )


class MemoryCache(RefreshableCache[CachedT]):
    """In-memory cache for ephemeral storage."""

    _storage: ClassVar[dict[str, CacheEntry[Any]]] = {}

    def _get_entry(self) -> CacheEntry[CachedT] | None:
        logger.debug(
            f"MemoryCache: getting entry for namespace='{self._namespace}', key='{self._key}'"
        )
        entry = self._storage.get(self._get_full_key())
        if entry is None:
            logger.debug(
                f"MemoryCache: cache miss for namespace='{self._namespace}', key='{self._key}'"
            )
            return None
        logger.debug(f"MemoryCache: cache hit for namespace='{self._namespace}', key='{self._key}'")
        return entry

    def set(self, value: CachedT) -> None:
        logger.debug(
            f"MemoryCache: setting entry for namespace='{self._namespace}', key='{self._key}'"
        )
        self._storage[self._get_full_key()] = CacheEntry(value=value, timestamp=time.time())
        logger.debug(
            f"MemoryCache: successfully set entry for "
            f"namespace='{self._namespace}', key='{self._key}'"
        )

    def delete(self) -> None:
        logger.debug(
            f"MemoryCache: deleting entry for namespace='{self._namespace}', key='{self._key}'"
        )
        self._storage.pop(self._get_full_key(), None)
        logger.debug(
            f"MemoryCache: successfully deleted entry for namespace='"
            f"{self._namespace}', key='{self._key}'"
        )


class NullCache(RefreshableCache[CachedT]):
    """Cache that doesn't cache anything (Null Object pattern).

    Useful as a final fallback when you want to explicitly disable caching.
    Reads always return None (triggering fetch), writes/deletes do nothing.
    """

    def _get_entry(self) -> CacheEntry[CachedT] | None:
        logger.debug(
            f"NullCache: cache miss (no-op) for namespace='{self._namespace}', key='{self._key}'"
        )
        return None

    def set(self, value: CachedT) -> None:
        _ = value  # Unused by design (Null Object pattern)
        logger.debug(
            f"NullCache: skipping set (no-op) for namespace='{self._namespace}', key='{self._key}'"
        )

    def delete(self) -> None:
        logger.debug(
            f"NullCache: skipping delete (no-op) for namespace='"
            f"{self._namespace}', key='{self._key}'"
        )


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
        fetch_fn: "Callable[[], CachedT] | FetchFn[CachedT]",
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
        logger.debug(f"ChainedCache: initializing with {len(backends)} backends for key='{key}'")
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
        logger.debug(
            f"ChainedCache: trying {len(self._backends)} backends for namespace='"
            f"{self._namespace}', key='{self._key}'"
        )
        for i, backend in enumerate(self._backends):
            try:
                entry = backend._get_entry()
                if entry is not None:
                    logger.debug(
                        f"ChainedCache: cache hit from backend {i} for namespace='"
                        f"{self._namespace}', key='{self._key}'"
                    )
                    return entry
            except Exception as e:
                logger.debug(
                    f"ChainedCache: backend {i} failed for namespace='"
                    f"{self._namespace}', key='{self._key}': {e}"
                )
                continue
        logger.debug(
            f"ChainedCache: cache miss across all backends for namespace='"
            f"{self._namespace}', key='{self._key}'"
        )
        return None

    def set(self, value: CachedT) -> None:
        logger.debug(
            f"ChainedCache: setting entry for namespace='{self._namespace}', key='{self._key}'"
        )
        for i, backend in enumerate(self._backends):
            try:
                backend.set(value)
                logger.debug(
                    f"ChainedCache: successfully set entry on backend {i} for "
                    f"namespace='{self._namespace}', key='{self._key}'"
                )
            except Exception as e:
                logger.debug(
                    f"ChainedCache: backend {i} failed to set for "
                    f"namespace='{self._namespace}', key='{self._key}': {e}"
                )
        logger.debug(
            f"ChainedCache: all backends failed to set for "
            f"namespace='{self._namespace}', key='{self._key}'"
        )

    def delete(self) -> None:
        logger.debug(
            f"ChainedCache: deleting entry for namespace='{self._namespace}', key='{self._key}'"
        )
        for i, backend in enumerate(self._backends):
            try:
                backend.delete()
                logger.debug(
                    f"ChainedCache: successfully deleted entry on backend {i} for "
                    f"namespace='{self._namespace}', key='{self._key}'"
                )
            except Exception as e:
                logger.debug(
                    f"ChainedCache: backend {i} failed to delete for "
                    f"namespace='{self._namespace}', key='{self._key}': {e}"
                )
