from collections.abc import Callable, KeysView
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar

from bakelib.refreshable_cache.cache import (
    DEFAULT_NAMESPACE,
    ChainedCache,
    KeyringCache,
    MemoryCache,
    RefreshableCache,
)
from bakelib.refreshable_cache.utils import FetchFn, NullFetchFn

if TYPE_CHECKING:
    from tenacity.stop import StopBaseT
    from tenacity.wait import WaitBaseT

T = TypeVar("T")


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

    def register(
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
            msg = f"Key '{key}' already registered; call unregister() first"
            raise ValueError(msg)
        if fetch_fn is None:
            fetch_fn = NullFetchFn(key)
        cache = self._build_cache(
            key=key, fetch_fn=fetch_fn, ttl=ttl, stop=stop, wait=wait, cached_type=cached_type
        )
        self._caches[key] = cache
        return cache

    def get_or_register(
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
        kwargs: dict[str, Any] = {
            k: v
            for k, v in (
                ("fetch_fn", fetch_fn),
                ("ttl", ttl),
                ("stop", stop),
                ("wait", wait),
                ("cached_type", cached_type),
            )
            if v is not None
        }
        return self.register(key, **kwargs)

    def _build_cache(
        self,
        key: str,
        fetch_fn: Callable[[], T] | FetchFn[T],
        ttl: float | None,
        stop: "StopBaseT | None",
        wait: "WaitBaseT | None",
        cached_type: Any,
    ) -> RefreshableCache[T]:
        kwargs: dict[str, Any] = {
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
        return ChainedCache(backends=self.backends, **kwargs)

    def cache(self, key: str) -> RefreshableCache[T]:
        try:
            return self._caches[key]
        except KeyError:
            msg = f"Key '{key}' not registered"
            raise KeyError(msg) from None

    def __contains__(self, key: object) -> bool:
        return key in self._caches

    def keys(self) -> KeysView[str]:
        return self._caches.keys()

    def is_cached(self, key: str) -> bool:
        cache = self._caches.get(key)
        return cache is not None and cache.has_value()

    def get(self, key: str) -> T:
        return self.cache(key).get_value()

    def delete(self, key: str) -> None:
        self.cache(key).delete()

    def delete_all(self) -> None:
        for cache in self._caches.values():
            cache.delete()

    def refresh(self, key: str) -> T:
        return self.cache(key).refresh()

    def refresh_all(self) -> None:
        for cache in self._caches.values():
            cache.refresh()

    def unregister(self, key: str) -> None:
        try:
            cache = self._caches.pop(key)
        except KeyError:
            msg = f"Key '{key}' not registered"
            raise KeyError(msg) from None
        cache.delete()


class SecretUtilsKeyringCacheRegistry(RefreshableCacheRegistry[T]):
    _backends: ClassVar[list[type[RefreshableCache[Any]]]] = [MemoryCache, KeyringCache]
    namespace: str = "bakebook"
