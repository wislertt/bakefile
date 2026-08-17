from collections.abc import Callable, KeysView
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar

from bakelib.refreshable_cache.cache import (
    DEFAULT_NAMESPACE,
    CacheKwargs,
    ChainedCache,
    ChainedCacheKwargs,
    KeyringCache,
    MemoryCache,
    RefreshableCache,
)
from bakelib.refreshable_cache.utils import FetchFn, NullFetchFn

if TYPE_CHECKING:
    from tenacity.stop import StopBaseT
    from tenacity.wait import WaitBaseT

T = TypeVar("T")


def _drop_none(**kwargs: Any) -> dict[str, Any]:
    return {k: v for k, v in kwargs.items() if v is not None}


class RefreshableCacheRegistry(Generic[T]):
    _backends: ClassVar[list[type[RefreshableCache[Any]]]] = [MemoryCache]
    namespace: str = DEFAULT_NAMESPACE
    ttl: float | None = None
    stop: "StopBaseT | None" = None
    wait: "WaitBaseT | None" = None
    cached_type: Any = None

    def __init__(
        self,
        *,
        namespace: str | None = None,
        backends: list[type[RefreshableCache[Any]]] | None = None,
        ttl: float | None = None,
        stop: "StopBaseT | None" = None,
        wait: "WaitBaseT | None" = None,
        cached_type: Any = None,
    ) -> None:
        if namespace is not None:
            self.namespace = namespace
        self.backends = backends if backends is not None else self.__class__._backends
        if ttl is not None:
            self.ttl = ttl
        if stop is not None:
            self.stop = stop
        if wait is not None:
            self.wait = wait
        if cached_type is not None:
            self.cached_type = cached_type
        self._caches: dict[str, RefreshableCache[T]] = {}

    # ── Handle (cache repo) ──

    def insert_cache(
        self,
        key: str,
        *,
        fetch_fn: Callable[[], T] | FetchFn[T] | None = None,
        ttl: float | None = None,
        stop: "StopBaseT | None" = None,
        wait: "WaitBaseT | None" = None,
        cached_type: Any = None,
    ) -> RefreshableCache[T]:
        if key in self._caches:
            msg = f"Key '{key}' already registered; call remove_cache() first"
            raise ValueError(msg)
        if fetch_fn is None:
            fetch_fn = NullFetchFn(key)
        cache = self._build_cache(
            key=key, fetch_fn=fetch_fn, ttl=ttl, stop=stop, wait=wait, cached_type=cached_type
        )
        self._caches[key] = cache
        return cache

    def ensure_cache(
        self,
        key: str,
        *,
        fetch_fn: Callable[[], T] | FetchFn[T] | None = None,
        ttl: float | None = None,
        stop: "StopBaseT | None" = None,
        wait: "WaitBaseT | None" = None,
        cached_type: Any = None,
    ) -> RefreshableCache[T]:
        existing = self._caches.get(key)
        if existing is not None:
            return existing
        return self.insert_cache(
            key,
            **_drop_none(fetch_fn=fetch_fn, ttl=ttl, stop=stop, wait=wait, cached_type=cached_type),
        )

    def upsert_cache(
        self,
        key: str,
        *,
        fetch_fn: Callable[[], T] | FetchFn[T] | None = None,
        ttl: float | None = None,
        stop: "StopBaseT | None" = None,
        wait: "WaitBaseT | None" = None,
        cached_type: Any = None,
    ) -> RefreshableCache[T]:
        if key in self._caches:
            self.remove_cache(key)
        return self.insert_cache(
            key,
            **_drop_none(fetch_fn=fetch_fn, ttl=ttl, stop=stop, wait=wait, cached_type=cached_type),
        )

    def remove_cache(self, key: str) -> None:
        try:
            cache = self._caches.pop(key)
        except KeyError:
            msg = f"Key '{key}' not registered"
            raise KeyError(msg) from None
        cache.delete()

    def get_cache(self, key: str) -> RefreshableCache[T]:
        try:
            return self._caches[key]
        except KeyError:
            msg = f"Key '{key}' not registered"
            raise KeyError(msg) from None

    def list_cache_keys(self) -> KeysView[str]:
        return self._caches.keys()

    def __contains__(self, key: object) -> bool:
        return key in self._caches

    # ── Value ──

    def get(self, key: str) -> T:
        return self.get_cache(key).get()

    def set(self, key: str, value: T) -> None:
        self.get_cache(key).set(value)

    def delete(self, key: str) -> None:
        self.get_cache(key).delete()

    def delete_all(self) -> None:
        for cache in self._caches.values():
            cache.delete()

    def refresh(self, key: str) -> T:
        return self.get_cache(key).refresh()

    def refresh_all(self) -> None:
        for cache in self._caches.values():
            cache.refresh()

    def has_value(self, key: str) -> bool:
        cache = self._caches.get(key)
        return cache is not None and cache.has_value()

    # ── Internal ──

    def _build_cache(
        self,
        key: str,
        fetch_fn: Callable[[], T] | FetchFn[T],
        ttl: float | None,
        stop: "StopBaseT | None",
        wait: "WaitBaseT | None",
        cached_type: Any,
    ) -> RefreshableCache[T]:
        kwargs: CacheKwargs = {
            "key": key,
            "fetch_fn": fetch_fn,
            "ttl": ttl if ttl is not None else self.ttl,
            "namespace": self.namespace,
            "stop": stop if stop is not None else self.stop,
            "wait": wait if wait is not None else self.wait,
            "cached_type": cached_type if cached_type is not None else self.cached_type,
        }
        if len(self.backends) == 1:
            return self.backends[0](**kwargs)
        chained_kwargs: ChainedCacheKwargs = {**kwargs, "backends": self.backends}
        return ChainedCache(**chained_kwargs)


class SecretUtilsKeyringCacheRegistry(RefreshableCacheRegistry[T]):
    _backends: ClassVar[list[type[RefreshableCache[Any]]]] = [MemoryCache, KeyringCache]
    namespace: str = "bakebook"
