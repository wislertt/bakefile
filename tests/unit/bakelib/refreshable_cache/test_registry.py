import functools
from dataclasses import dataclass

import pytest
from tenacity import stop_after_attempt, wait_fixed

from bakelib.refreshable_cache import (
    ChainedCache,
    FetchFn,
    KeyringCache,
    MemoryCache,
    RefreshableCache,
    RefreshableCacheRegistry,
)


def key_fetch(key: str) -> str:
    return f"val-{key}"


class _KeyRegistry(RefreshableCacheRegistry[str]):
    def register(self, key: str, **kw):
        kw.setdefault("fetch_fn", lambda k=key: key_fetch(k))
        return super().register(key, **kw)


def make_registry(
    namespace: str,
    *,
    backends: list[type[RefreshableCache]] | None = None,
    **kwargs,
) -> _KeyRegistry:
    if backends is None:
        backends = [MemoryCache]
    defaults: dict = {"cached_type": str}
    defaults.update(kwargs)
    return _KeyRegistry(
        namespace=namespace,
        backends=backends,
        **defaults,
    )


class TestRegistryBuild:
    def test_single_backend_builds_direct_backend(self):
        registry = make_registry("reg-build-single", backends=[MemoryCache])
        cache = registry.register("k")
        assert isinstance(cache, MemoryCache)
        assert not isinstance(cache, ChainedCache)

    def test_multiple_backends_build_chained_cache(self):
        registry = make_registry("reg-build-chained", backends=[MemoryCache, KeyringCache])
        cache = registry.register("k")
        assert isinstance(cache, ChainedCache)
        assert [type(b) for b in cache._backends] == [MemoryCache, KeyringCache]

    def test_default_backends_is_memory(self):
        registry = RefreshableCacheRegistry(namespace="reg-build-default", cached_type=str)
        cache = registry.register("k", fetch_fn=lambda: "v")
        assert isinstance(cache, MemoryCache)

    def test_namespace_threaded_to_backend(self):
        registry = make_registry("reg-ns")
        cache = registry.register("k")
        assert cache._namespace == "reg-ns"


class TestRegistryRegister:
    def test_register_returns_cache_and_keys(self):
        registry = make_registry("reg-keys")
        registry.register("a")
        registry.register("b")
        assert set(registry.keys()) == {"a", "b"}

    def test_duplicate_register_raises(self):
        registry = make_registry("reg-dup")
        registry.register("a")
        with pytest.raises(ValueError, match="already registered"):
            registry.register("a")

    def test_cache_returns_underlying_handle(self):
        registry = make_registry("reg-handle")
        registered = registry.register("a")
        assert registry.cache("a") is registered

    def test_cache_missing_raises(self):
        registry = make_registry("reg-missing")
        with pytest.raises(KeyError, match="not registered"):
            registry.cache("nope")

    def test_register_rejects_fetch_fn_with_mismatched_key(self):
        @dataclass(frozen=True)
        class KeyedFetch(FetchFn[str]):
            def __call__(self) -> str:
                return f"v-{self.key}"

        registry = make_registry("reg-key-mismatch")
        with pytest.raises(ValueError, match="does not match key"):
            registry.register("slot-a", fetch_fn=KeyedFetch(key="slot-b"))


class TestRegistryPolicy:
    def test_ttl_default_inherited_from_registry(self):
        registry = make_registry("reg-ttl-default", ttl=42)
        cache = registry.register("k")
        assert cache._ttl == 42

    def test_ttl_override_wins(self):
        registry = make_registry("reg-ttl-override", ttl=42)
        cache = registry.register("k", ttl=7)
        assert cache._ttl == 7
        assert registry.register("k2")._ttl == 42

    def test_stop_default_inherited_from_registry(self):
        my_stop = stop_after_attempt(5)
        registry = make_registry("reg-stop-default", stop=my_stop)
        cache = registry.register("k")
        assert cache._stop is my_stop

    def test_stop_override_wins(self):
        registry_stop = stop_after_attempt(5)
        override_stop = stop_after_attempt(9)
        registry = make_registry("reg-stop-override", stop=registry_stop)
        cache = registry.register("k", stop=override_stop)
        assert cache._stop is override_stop
        assert cache._stop is not registry_stop

    def test_wait_default_inherited_from_registry(self):
        my_wait = wait_fixed(2)
        registry = make_registry("reg-wait-default", wait=my_wait)
        cache = registry.register("k")
        assert cache._wait is my_wait

    def test_cached_type_override_wins(self):
        registry = make_registry("reg-type", cached_type=str)
        registry.register("k", cached_type=int, fetch_fn=lambda: 5)
        value = registry.get("k")
        assert value == 5
        assert isinstance(value, int)


class TestRegistryFetchSpec:
    def test_fetch_fn_builds_value(self):
        registry = make_registry("reg-spec-fn")
        registry.register("alpha", fetch_fn=lambda: "fetched-alpha")
        assert registry.get("alpha") == "fetched-alpha"

    def test_get_returns_cached_without_refetch(self):
        calls = 0

        def fetch() -> str:
            nonlocal calls
            calls += 1
            return "v-k"

        registry = make_registry("reg-spec-cached")
        registry.register("k", fetch_fn=fetch)
        assert registry.get("k") == "v-k"
        assert registry.get("k") == "v-k"
        assert calls == 1

    def test_register_without_fetch_fn_defaults_to_null(self):
        registry = RefreshableCacheRegistry(
            namespace="reg-spec-none", backends=[MemoryCache], cached_type=str
        )
        cache = registry.register("k")
        assert cache.get_value() is None

    def test_subclass_with_fetch_spec_cls_builds_from_key(self):
        built: list[str] = []

        @dataclass(frozen=True)
        class RecordingKeyFetch(FetchFn[str]):
            def __post_init__(self):
                built.append(self.key)

            def __call__(self) -> str:
                return f"fetched-{self.key}"

        class KeyRegistry(RefreshableCacheRegistry[str]):
            def register(self, key: str, **kw):
                kw.setdefault("fetch_fn", RecordingKeyFetch(key))
                return super().register(key, **kw)

        registry = KeyRegistry(
            namespace="reg-spec-subclass", backends=[MemoryCache], cached_type=str
        )
        registry.register("alpha")
        assert built == ["alpha"]
        assert registry.get("alpha") == "fetched-alpha"


class TestRegistryIsCached:
    def test_not_cached_before_get(self):
        registry = make_registry("reg-status-before")
        registry.register("k")
        assert registry.is_cached("k") is False

    def test_cached_after_get(self):
        registry = make_registry("reg-status-after")
        registry.register("k")
        registry.get("k")
        assert registry.is_cached("k") is True

    def test_not_cached_after_delete(self):
        registry = make_registry("reg-status-del")
        registry.register("k")
        registry.get("k")
        registry.delete("k")
        assert registry.is_cached("k") is False

    def test_not_cached_for_unregistered_key(self):
        registry = make_registry("reg-status-missing")
        assert registry.is_cached("nope") is False


class TestRegistryMutation:
    def test_delete_clears_value(self):
        registry = make_registry("reg-delete")
        registry.register("k")
        registry.get("k")
        assert registry.is_cached("k") is True
        registry.delete("k")
        assert registry.is_cached("k") is False

    def test_delete_missing_key_raises(self):
        registry = make_registry("reg-delete-missing")
        with pytest.raises(KeyError, match="not registered"):
            registry.delete("nope")

    def test_delete_all_clears_all(self):
        registry = make_registry("reg-delete-all")
        registry.register("a")
        registry.register("b")
        registry.get("a")
        registry.get("b")
        registry.delete_all()
        assert registry.is_cached("a") is False
        assert registry.is_cached("b") is False
        assert set(registry.keys()) == {"a", "b"}

    def test_refresh_forces_refetch(self):
        calls = 0

        def counting_fetch() -> str:
            nonlocal calls
            calls += 1
            return f"v{calls}-k"

        registry = make_registry("reg-refresh")
        registry.register("k", fetch_fn=counting_fetch)
        assert registry.get("k") == "v1-k"
        assert registry.refresh("k") == "v2-k"
        assert registry.get("k") == "v2-k"

    def test_refresh_all_refreshes_each(self):
        calls = 0

        def counting_fetch() -> str:
            nonlocal calls
            calls += 1
            return f"v{calls}"

        registry = make_registry("reg-refresh-all")
        registry.register("a", fetch_fn=counting_fetch)
        registry.register("b", fetch_fn=counting_fetch)
        registry.get("a")
        registry.get("b")
        assert calls == 2
        registry.refresh_all()
        assert calls == 4
        assert registry.is_cached("a") is True
        assert registry.is_cached("b") is True

    def test_unregister_removes_handle_and_value(self):
        registry = make_registry("reg-unregister")
        registry.register("k")
        registry.get("k")
        registry.unregister("k")
        assert "k" not in registry
        assert registry.is_cached("k") is False
        with pytest.raises(KeyError, match="not registered"):
            registry.cache("k")

    def test_unregister_clears_cached_value(self):
        registry = make_registry("reg-unregister-value")
        cache = registry.register("k")
        registry.get("k")
        assert cache.has_value() is True
        registry.unregister("k")
        assert cache.has_value() is False

    def test_unregister_missing_raises(self):
        registry = make_registry("reg-unregister-missing")
        with pytest.raises(KeyError, match="not registered"):
            registry.unregister("nope")


class TestRegistryHeterogeneousFetch:
    def test_entries_use_different_fetch_sources_and_arg_shapes(self):
        def two_arg_fetcher(project_id: str, secret_id: str) -> str:
            return f"{project_id}:{secret_id}"

        def one_arg_fetcher(name: str) -> str:
            return f"env-{name}"

        registry = make_registry("reg-hetero-src")
        registry.register("a")
        registry.register("b", fetch_fn=lambda: two_arg_fetcher("proj-1", "secret-b"))
        registry.register("c", fetch_fn=lambda: one_arg_fetcher("API_TOKEN"))

        assert registry.get("a") == "val-a"
        assert registry.get("b") == "proj-1:secret-b"
        assert registry.get("c") == "env-API_TOKEN"

    def test_fetch_fn_override_is_used(self):
        registry = make_registry("reg-hetero-ignore")
        registry.register("a", fetch_fn=lambda: "override-only")
        assert registry.get("a") == "override-only"

    def test_subclass_branches_on_key_for_different_sources(self):
        def branching_fetch(key: str) -> str:
            if key.startswith("sm/"):
                return f"secret-manager:{key}"
            if key.startswith("env/"):
                return f"env-var:{key}"
            return f"default:{key}"

        class BranchingRegistry(RefreshableCacheRegistry[str]):
            def register(self, key: str, **kw):
                kw.setdefault("fetch_fn", lambda k=key: branching_fetch(k))
                return super().register(key, **kw)

        registry = BranchingRegistry(
            namespace="reg-hetero-branch", backends=[MemoryCache], cached_type=str
        )
        registry.register("sm/db")
        registry.register("env/API")
        registry.register("plain")

        assert registry.get("sm/db") == "secret-manager:sm/db"
        assert registry.get("env/API") == "env-var:env/API"
        assert registry.get("plain") == "default:plain"

    def test_two_arg_fetcher_via_functools_partial(self):
        def get_secret(project_id: str, secret_id: str) -> str:
            return f"{project_id}/{secret_id}"

        registry = make_registry("reg-hetero-partial")
        registry.register(
            "db",
            fetch_fn=functools.partial(get_secret, project_id="proj-1", secret_id="db"),
        )
        assert registry.get("db") == "proj-1/db"
