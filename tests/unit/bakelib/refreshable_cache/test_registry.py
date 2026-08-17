import functools
import inspect
from dataclasses import dataclass

import pytest
from tenacity import stop_after_attempt, wait_fixed

from bakelib.refreshable_cache import (
    CacheKwargs,
    ChainedCache,
    ChainedCacheKwargs,
    FetchFn,
    KeyringCache,
    MemoryCache,
    RefreshableCache,
    RefreshableCacheRegistry,
)


def key_fetch(key: str) -> str:
    return f"val-{key}"


class _KeyRegistry(RefreshableCacheRegistry[str]):
    def insert_cache(self, key: str, **kw):
        kw.setdefault("fetch_fn", lambda k=key: key_fetch(k))
        return super().insert_cache(key, **kw)


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
        cache = registry.insert_cache("k")
        assert isinstance(cache, MemoryCache)
        assert not isinstance(cache, ChainedCache)

    def test_multiple_backends_build_chained_cache(self):
        registry = make_registry("reg-build-chained", backends=[MemoryCache, KeyringCache])
        cache = registry.insert_cache("k")
        assert isinstance(cache, ChainedCache)
        assert [type(b) for b in cache._backends] == [MemoryCache, KeyringCache]

    def test_default_backends_is_memory(self):
        registry = RefreshableCacheRegistry(namespace="reg-build-default", cached_type=str)
        cache = registry.insert_cache("k", fetch_fn=lambda: "v")
        assert isinstance(cache, MemoryCache)

    def test_namespace_threaded_to_backend(self):
        registry = make_registry("reg-ns")
        cache = registry.insert_cache("k")
        assert cache._namespace == "reg-ns"


class TestRegistryRegister:
    def test_register_returns_cache_and_keys(self):
        registry = make_registry("reg-keys")
        registry.insert_cache("a")
        registry.insert_cache("b")
        assert set(registry.list_cache_keys()) == {"a", "b"}

    def test_duplicate_register_raises(self):
        registry = make_registry("reg-dup")
        registry.insert_cache("a")
        with pytest.raises(ValueError, match="already registered"):
            registry.insert_cache("a")

    def test_cache_returns_underlying_handle(self):
        registry = make_registry("reg-handle")
        registered = registry.insert_cache("a")
        assert registry.get_cache("a") is registered

    def test_cache_missing_raises(self):
        registry = make_registry("reg-missing")
        with pytest.raises(KeyError, match="not registered"):
            registry.get_cache("nope")

    def test_register_rejects_fetch_fn_with_mismatched_key(self):
        @dataclass(frozen=True)
        class KeyedFetch(FetchFn[str]):
            def __call__(self) -> str:
                return f"v-{self.key}"

        registry = make_registry("reg-key-mismatch")
        with pytest.raises(ValueError, match="does not match key"):
            registry.insert_cache("slot-a", fetch_fn=KeyedFetch(key="slot-b"))


class TestRegistryGetOrRegister:
    def test_registers_when_absent(self):
        registry = make_registry("reg-gor-absent")
        cache = registry.ensure_cache("k", fetch_fn=lambda: "v-k")
        assert "k" in registry
        assert registry.get("k") == "v-k"
        assert registry.get_cache("k") is cache

    def test_returns_existing_when_present(self):
        registry = make_registry("reg-gor-existing")
        first = registry.insert_cache("k", fetch_fn=lambda: "first")
        again = registry.ensure_cache("k", fetch_fn=lambda: "second")
        assert again is first

    def test_idempotent_returns_same_instance(self):
        registry = make_registry("reg-gor-idempotent")
        a = registry.ensure_cache("k", fetch_fn=lambda: "v")
        b = registry.ensure_cache("k", fetch_fn=lambda: "v")
        assert a is b

    def test_existing_fetch_fn_preserved(self):
        registry = make_registry("reg-gor-preserve")
        registry.insert_cache("k", fetch_fn=lambda: "first")
        registry.ensure_cache("k", fetch_fn=lambda: "second")
        assert registry.get("k") == "first"

    def test_preserves_subclass_fetch_fn_default(self):
        # _KeyRegistry injects a key-derived fetch_fn inside register();
        # ensure_cache must forward absent kwargs as absent (not fetch_fn=None),
        # else the subclass default is shadowed.
        registry = make_registry("reg-gor-subclass")
        registry.ensure_cache("k")
        assert registry.get("k") == "val-k"

    def test_signature_matches_insert_cache(self):
        assert inspect.signature(RefreshableCacheRegistry.ensure_cache) == inspect.signature(
            RefreshableCacheRegistry.insert_cache
        )


class TestRegistryUpsert:
    def test_registers_when_absent(self):
        registry = make_registry("reg-upsert-absent")
        cache = registry.upsert_cache("k", fetch_fn=lambda: "v-k")
        assert "k" in registry
        assert registry.get("k") == "v-k"
        assert registry.get_cache("k") is cache

    def test_replaces_when_present(self):
        registry = make_registry("reg-upsert-replace")
        first = registry.insert_cache("k", fetch_fn=lambda: "first")
        registry.get("k")
        replaced = registry.upsert_cache("k", fetch_fn=lambda: "second")
        assert replaced is not first
        assert registry.get_cache("k") is replaced
        assert registry.get("k") == "second"

    def test_old_cache_value_cleared_after_replace(self):
        registry = make_registry("reg-upsert-cleanup")
        old = registry.insert_cache("k", fetch_fn=lambda: "first")
        registry.get("k")
        assert old.has_value() is True
        registry.upsert_cache("k", fetch_fn=lambda: "second")
        assert old.has_value() is False

    def test_preserves_subclass_fetch_fn_default(self):
        registry = make_registry("reg-upsert-subclass")
        registry.upsert_cache("k")
        assert registry.get("k") == "val-k"

    def test_replaces_then_registers_clean(self):
        registry = make_registry("reg-upsert-repeat")
        registry.upsert_cache("k", fetch_fn=lambda: "v1")
        registry.upsert_cache("k", fetch_fn=lambda: "v2")
        assert registry.get("k") == "v2"
        assert set(registry.list_cache_keys()) == {"k"}

    def test_signature_matches_insert_cache(self):
        assert inspect.signature(RefreshableCacheRegistry.upsert_cache) == inspect.signature(
            RefreshableCacheRegistry.insert_cache
        )


class TestRegistrySignatureParity:
    def test_handle_methods_share_signature(self):
        sig = inspect.signature
        insert = sig(RefreshableCacheRegistry.insert_cache)
        assert sig(RefreshableCacheRegistry.ensure_cache) == insert
        assert sig(RefreshableCacheRegistry.upsert_cache) == insert


class TestCacheKwargs:
    """CacheKwargs/ChainedCacheKwargs should stay in sync with cache __init__ signatures."""

    def test_cache_kwargs_matches_refreshable_cache_params(self):
        init_params = set(inspect.signature(RefreshableCache.__init__).parameters)
        kwargs_keys = set(CacheKwargs.__annotations__)

        unexpected = kwargs_keys - init_params
        assert not unexpected, (
            f"CacheKwargs has params RefreshableCache doesn't accept: {sorted(unexpected)}"
        )

        missing = init_params - kwargs_keys - {"self"}
        assert not missing, (
            f"RefreshableCache.__init__ has params missing from CacheKwargs: {sorted(missing)}"
        )

    def test_chained_cache_kwargs_matches_chained_cache_params(self):
        init_params = set(inspect.signature(ChainedCache.__init__).parameters)
        kwargs_keys = set(ChainedCacheKwargs.__annotations__)

        unexpected = kwargs_keys - init_params
        assert not unexpected, (
            f"ChainedCacheKwargs has params ChainedCache doesn't accept: {sorted(unexpected)}"
        )

        missing = init_params - kwargs_keys - {"self"}
        assert not missing, (
            f"ChainedCache.__init__ has params missing from ChainedCacheKwargs: {sorted(missing)}"
        )


class TestRegistryPolicy:
    def test_ttl_default_inherited_from_registry(self):
        registry = make_registry("reg-ttl-default", ttl=42)
        cache = registry.insert_cache("k")
        assert cache._ttl == 42

    def test_ttl_override_wins(self):
        registry = make_registry("reg-ttl-override", ttl=42)
        cache = registry.insert_cache("k", ttl=7)
        assert cache._ttl == 7
        assert registry.insert_cache("k2")._ttl == 42

    def test_stop_default_inherited_from_registry(self):
        my_stop = stop_after_attempt(5)
        registry = make_registry("reg-stop-default", stop=my_stop)
        cache = registry.insert_cache("k")
        assert cache._stop is my_stop

    def test_stop_override_wins(self):
        registry_stop = stop_after_attempt(5)
        override_stop = stop_after_attempt(9)
        registry = make_registry("reg-stop-override", stop=registry_stop)
        cache = registry.insert_cache("k", stop=override_stop)
        assert cache._stop is override_stop
        assert cache._stop is not registry_stop

    def test_wait_default_inherited_from_registry(self):
        my_wait = wait_fixed(2)
        registry = make_registry("reg-wait-default", wait=my_wait)
        cache = registry.insert_cache("k")
        assert cache._wait is my_wait

    def test_cached_type_override_wins(self):
        registry = make_registry("reg-type", cached_type=str)
        registry.insert_cache("k", cached_type=int, fetch_fn=lambda: 5)
        value = registry.get("k")
        assert value == 5
        assert isinstance(value, int)


class TestRegistryFetchSpec:
    def test_fetch_fn_builds_value(self):
        registry = make_registry("reg-spec-fn")
        registry.insert_cache("alpha", fetch_fn=lambda: "fetched-alpha")
        assert registry.get("alpha") == "fetched-alpha"

    def test_get_returns_cached_without_refetch(self):
        calls = 0

        def fetch() -> str:
            nonlocal calls
            calls += 1
            return "v-k"

        registry = make_registry("reg-spec-cached")
        registry.insert_cache("k", fetch_fn=fetch)
        assert registry.get("k") == "v-k"
        assert registry.get("k") == "v-k"
        assert calls == 1

    def test_register_without_fetch_fn_defaults_to_null(self):
        registry = RefreshableCacheRegistry(
            namespace="reg-spec-none", backends=[MemoryCache], cached_type=str
        )
        cache = registry.insert_cache("k")
        assert cache.get() is None

    def test_subclass_with_fetch_spec_cls_builds_from_key(self):
        built: list[str] = []

        @dataclass(frozen=True)
        class RecordingKeyFetch(FetchFn[str]):
            def __post_init__(self):
                built.append(self.key)

            def __call__(self) -> str:
                return f"fetched-{self.key}"

        class KeyRegistry(RefreshableCacheRegistry[str]):
            def insert_cache(self, key: str, **kw):
                kw.setdefault("fetch_fn", RecordingKeyFetch(key))
                return super().insert_cache(key, **kw)

        registry = KeyRegistry(
            namespace="reg-spec-subclass", backends=[MemoryCache], cached_type=str
        )
        registry.insert_cache("alpha")
        assert built == ["alpha"]
        assert registry.get("alpha") == "fetched-alpha"


class TestRegistryHasValue:
    def test_not_cached_before_get(self):
        registry = make_registry("reg-status-before")
        registry.insert_cache("k")
        assert registry.has_value("k") is False

    def test_cached_after_get(self):
        registry = make_registry("reg-status-after")
        registry.insert_cache("k")
        registry.get("k")
        assert registry.has_value("k") is True

    def test_not_cached_after_delete(self):
        registry = make_registry("reg-status-del")
        registry.insert_cache("k")
        registry.get("k")
        registry.delete("k")
        assert registry.has_value("k") is False

    def test_not_cached_for_unregistered_key(self):
        registry = make_registry("reg-status-missing")
        assert registry.has_value("nope") is False


class TestRegistrySet:
    def test_set_stores_value_visible_to_get(self):
        registry = make_registry("reg-set-value")
        registry.insert_cache("k", fetch_fn=lambda: "fetched")
        registry.set("k", "manual")
        assert registry.get("k") == "manual"

    def test_set_marks_has_value_true(self):
        registry = make_registry("reg-set-has-value")
        registry.insert_cache("k")
        assert registry.has_value("k") is False
        registry.set("k", "manual")
        assert registry.has_value("k") is True

    def test_set_missing_key_raises(self):
        registry = make_registry("reg-set-missing")
        with pytest.raises(KeyError, match="not registered"):
            registry.set("nope", "manual")


class TestRegistryMutation:
    def test_delete_clears_value(self):
        registry = make_registry("reg-delete")
        registry.insert_cache("k")
        registry.get("k")
        assert registry.has_value("k") is True
        registry.delete("k")
        assert registry.has_value("k") is False

    def test_delete_missing_key_raises(self):
        registry = make_registry("reg-delete-missing")
        with pytest.raises(KeyError, match="not registered"):
            registry.delete("nope")

    def test_delete_all_clears_all(self):
        registry = make_registry("reg-delete-all")
        registry.insert_cache("a")
        registry.insert_cache("b")
        registry.get("a")
        registry.get("b")
        registry.delete_all()
        assert registry.has_value("a") is False
        assert registry.has_value("b") is False
        assert set(registry.list_cache_keys()) == {"a", "b"}

    def test_refresh_forces_refetch(self):
        calls = 0

        def counting_fetch() -> str:
            nonlocal calls
            calls += 1
            return f"v{calls}-k"

        registry = make_registry("reg-refresh")
        registry.insert_cache("k", fetch_fn=counting_fetch)
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
        registry.insert_cache("a", fetch_fn=counting_fetch)
        registry.insert_cache("b", fetch_fn=counting_fetch)
        registry.get("a")
        registry.get("b")
        assert calls == 2
        registry.refresh_all()
        assert calls == 4
        assert registry.has_value("a") is True
        assert registry.has_value("b") is True

    def test_unregister_removes_handle_and_value(self):
        registry = make_registry("reg-unregister")
        registry.insert_cache("k")
        registry.get("k")
        registry.remove_cache("k")
        assert "k" not in registry
        assert registry.has_value("k") is False
        with pytest.raises(KeyError, match="not registered"):
            registry.get_cache("k")

    def test_unregister_clears_cached_value(self):
        registry = make_registry("reg-unregister-value")
        cache = registry.insert_cache("k")
        registry.get("k")
        assert cache.has_value() is True
        registry.remove_cache("k")
        assert cache.has_value() is False

    def test_unregister_missing_raises(self):
        registry = make_registry("reg-unregister-missing")
        with pytest.raises(KeyError, match="not registered"):
            registry.remove_cache("nope")


class TestRegistryHeterogeneousFetch:
    def test_entries_use_different_fetch_sources_and_arg_shapes(self):
        def two_arg_fetcher(project_id: str, secret_id: str) -> str:
            return f"{project_id}:{secret_id}"

        def one_arg_fetcher(name: str) -> str:
            return f"env-{name}"

        registry = make_registry("reg-hetero-src")
        registry.insert_cache("a")
        registry.insert_cache("b", fetch_fn=lambda: two_arg_fetcher("proj-1", "secret-b"))
        registry.insert_cache("c", fetch_fn=lambda: one_arg_fetcher("API_TOKEN"))

        assert registry.get("a") == "val-a"
        assert registry.get("b") == "proj-1:secret-b"
        assert registry.get("c") == "env-API_TOKEN"

    def test_fetch_fn_override_is_used(self):
        registry = make_registry("reg-hetero-ignore")
        registry.insert_cache("a", fetch_fn=lambda: "override-only")
        assert registry.get("a") == "override-only"

    def test_subclass_branches_on_key_for_different_sources(self):
        def branching_fetch(key: str) -> str:
            if key.startswith("sm/"):
                return f"secret-manager:{key}"
            if key.startswith("env/"):
                return f"env-var:{key}"
            return f"default:{key}"

        class BranchingRegistry(RefreshableCacheRegistry[str]):
            def insert_cache(self, key: str, **kw):
                kw.setdefault("fetch_fn", lambda k=key: branching_fetch(k))
                return super().insert_cache(key, **kw)

        registry = BranchingRegistry(
            namespace="reg-hetero-branch", backends=[MemoryCache], cached_type=str
        )
        registry.insert_cache("sm/db")
        registry.insert_cache("env/API")
        registry.insert_cache("plain")

        assert registry.get("sm/db") == "secret-manager:sm/db"
        assert registry.get("env/API") == "env-var:env/API"
        assert registry.get("plain") == "default:plain"

    def test_two_arg_fetcher_via_functools_partial(self):
        def get_secret(project_id: str, secret_id: str) -> str:
            return f"{project_id}/{secret_id}"

        registry = make_registry("reg-hetero-partial")
        registry.insert_cache(
            "db",
            fetch_fn=functools.partial(get_secret, project_id="proj-1", secret_id="db"),
        )
        assert registry.get("db") == "proj-1/db"
