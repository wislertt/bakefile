"""Unit tests for refreshable_cache module."""

import contextlib
import logging
import time
from typing import ClassVar

import keyring
import pytest
from keyring.errors import NoKeyringError

from bake.ui.logger import capsys_to_logs, has_messages_in_logs, setup_logging
from bakelib.refreshable_cache import (
    ChainedCache,
    KeyringCache,
    MemoryCache,
    NullCache,
    RefreshableCache,
)
from bakelib.refreshable_cache.cache import DEFAULT_NAMESPACE


def keyring_backend_available() -> bool:
    """Check if a keyring backend is available."""
    try:
        keyring.get_password("__test__", "__test__")
        return True
    except NoKeyringError:
        return False


skip_if_no_keyring = pytest.mark.skipif(
    not keyring_backend_available(), reason="No keyring backend available"
)


class TestKeyRegistry:
    _prefix = "test-cache"
    _all_keys: ClassVar[list[str]] = []

    @classmethod
    def create(cls, suffix: str) -> str:
        key = f"{cls._prefix}-{suffix}"
        cls._all_keys.append(key)
        return key

    @classmethod
    def get_all_keys(cls) -> list[str]:
        return cls._all_keys.copy()

    @classmethod
    def reset_all(cls) -> None:
        cls._all_keys.clear()


# Test key constants
KEY_BASE = TestKeyRegistry.create("base")
KEY_TTL = TestKeyRegistry.create("ttl")
KEY_NO_TTL = TestKeyRegistry.create("no-ttl")
KEY_NO_ERROR = TestKeyRegistry.create("no-error")
KEY_DECORATOR = TestKeyRegistry.create("decorator")
KEY_DELETE = TestKeyRegistry.create("delete")
KEY_DECORATOR_ONCE = TestKeyRegistry.create("once")
KEY_DECORATOR_CACHE_DELETE = TestKeyRegistry.create("cache-delete")
KEY_PERSIST = TestKeyRegistry.create("persist")
KEY_CACHED_TYPE_TEST = TestKeyRegistry.create("cached-type-test")
KEY_NO_TYPE = TestKeyRegistry.create("no-type")
KEY_A = TestKeyRegistry.create("a")
KEY_B = TestKeyRegistry.create("b")

# Keyring namespace constants
KEY_NAMESPACE_CUSTOM = "my-app"
KEY_CUSTOM = TestKeyRegistry.create("custom-namespace-custom")


@pytest.fixture(autouse=True, scope="session")
def cleanup_keyring():
    yield

    for key in TestKeyRegistry.get_all_keys():
        with contextlib.suppress(Exception):
            keyring.delete_password(DEFAULT_NAMESPACE, key)

    with contextlib.suppress(Exception):
        keyring.delete_password(KEY_NAMESPACE_CUSTOM, KEY_CUSTOM)

    TestKeyRegistry.reset_all()


class TestCacheBasics:
    """Tests for basic cache functionality."""

    @pytest.mark.parametrize(
        "cache_class", [MemoryCache] + ([KeyringCache] if keyring_backend_available() else [])
    )
    def test_cache_stores_and_retrieves_value(self, cache_class: type[RefreshableCache]):
        fetch_count = 0

        def fetch_value() -> str:
            nonlocal fetch_count
            fetch_count += 1
            return "test-value"

        cache = cache_class(KEY_BASE, fetch_value)
        assert cache.get_value() == "test-value"
        assert fetch_count == 1

        assert cache.get_value() == "test-value"
        assert fetch_count == 1

    @pytest.mark.parametrize(
        "cache_class,ttl",
        [(MemoryCache, 0.01)] + ([(KeyringCache, 0.05)] if keyring_backend_available() else []),
    )
    def test_cache_respects_ttl(
        self, cache_class: type[RefreshableCache], ttl: float, capsys: pytest.CaptureFixture[str]
    ):
        setup_logging(
            level_per_module={"": logging.WARNING, "bakelib": logging.DEBUG}, is_pretty_log=False
        )

        def fetch_value() -> str:
            return "test-value"

        cache = cache_class(KEY_TTL, fetch_value, ttl=ttl)
        _ = capsys.readouterr()

        cache.get_value()
        cache.get_value()
        logs = capsys_to_logs(capsys)
        assert has_messages_in_logs(logs, ["Cache miss", "Refreshing value", "Cache hit"])

        time.sleep(ttl + 0.01)
        cache.get_value()

        logs = capsys_to_logs(capsys)
        assert has_messages_in_logs(logs, ["Cache expired"])

    @pytest.mark.parametrize(
        "cache_class", [MemoryCache] + ([KeyringCache] if keyring_backend_available() else [])
    )
    def test_cache_with_none_ttl_never_expires(
        self, cache_class: type[RefreshableCache], capsys: pytest.CaptureFixture[str]
    ):
        setup_logging(
            level_per_module={"": logging.WARNING, "bakelib": logging.DEBUG}, is_pretty_log=False
        )

        def fetch_value() -> str:
            return "test-value"

        cache = cache_class(KEY_NO_TTL, fetch_value, ttl=None)
        _ = capsys.readouterr()

        cache.get_value()
        cache.get_value()

        logs = capsys_to_logs(capsys)
        assert has_messages_in_logs(logs, ["Cache miss", "Cache hit"])

    def test_memory_cache_multiple_instances_independent(self):
        fetch_counts = {"a": 0, "b": 0}

        def fetch_a() -> str:
            fetch_counts["a"] += 1
            return "a"

        def fetch_b() -> str:
            fetch_counts["b"] += 1
            return "b"

        cache_a = MemoryCache(KEY_A, fetch_a)
        cache_b = MemoryCache(KEY_B, fetch_b)

        assert cache_a.get_value() == "a"
        assert cache_b.get_value() == "b"
        assert fetch_counts == {"a": 1, "b": 1}

    def test_memory_cache_can_be_deleted(self):
        fetch_count = 0

        def fetch_value() -> str:
            nonlocal fetch_count
            fetch_count += 1
            return "value"

        cache = MemoryCache(KEY_DELETE, fetch_value)
        cache.get_value()
        assert fetch_count == 1

        cache.delete()
        cache.get_value()
        assert fetch_count == 2


class TestDecorator:
    """Tests for @cache.catch_refresh decorator."""

    @pytest.mark.parametrize(
        "cache_class", [MemoryCache] + ([KeyringCache] if keyring_backend_available() else [])
    )
    def test_catch_refresh_retries_on_error(self, cache_class: type[RefreshableCache]):
        call_count = 0
        fetch_count = 0

        def fetch_value() -> str:
            nonlocal fetch_count
            fetch_count += 1
            return "fresh-value"

        cache = cache_class(KEY_DECORATOR, fetch_value)

        @cache.catch_refresh
        def api_call(should_fail_first: bool = False) -> str:
            nonlocal call_count
            call_count += 1
            value = cache.get_value()
            if should_fail_first and call_count == 1:
                raise cache.RefreshNeededError("Value expired")
            return f"success-{value}"

        result = api_call(should_fail_first=True)
        assert result == "success-fresh-value"
        assert call_count == 2
        assert fetch_count == 2

    @pytest.mark.parametrize(
        "cache_class", [MemoryCache] + ([KeyringCache] if keyring_backend_available() else [])
    )
    def test_catch_refresh_no_error(self, cache_class: type[RefreshableCache]):
        fetch_count = 0

        def fetch_value() -> str:
            nonlocal fetch_count
            fetch_count += 1
            return "value"

        cache = cache_class(KEY_NO_ERROR, fetch_value)

        @cache.catch_refresh
        def api_call() -> str:
            return f"success-{cache.get_value()}"

        result = api_call()
        assert result == "success-value"
        assert fetch_count == 1

    def test_catch_refresh_only_retries_once(self):
        call_count = 0
        fetch_count = 0

        def fetch_value() -> str:
            nonlocal fetch_count
            fetch_count += 1
            return f"v{fetch_count}"

        cache = MemoryCache(KEY_DECORATOR_ONCE, fetch_value)

        @cache.catch_refresh
        def operation() -> str:
            nonlocal call_count
            call_count += 1
            raise cache.RefreshNeededError("Always fail")

        with pytest.raises(cache.RefreshNeededError):
            operation()

        assert call_count == 2
        assert fetch_count == 0

    @pytest.mark.parametrize(
        "cache_class", [MemoryCache] + ([KeyringCache] if keyring_backend_available() else [])
    )
    def test_catch_refresh_deletes_cache_after_last_retry_fails(
        self,
        cache_class: type[RefreshableCache],
    ):
        fetch_count = 0

        def fetch_value() -> str:
            nonlocal fetch_count
            fetch_count += 1
            return f"value-{fetch_count}"

        cache = cache_class(KEY_DECORATOR_CACHE_DELETE, fetch_value)

        @cache.catch_refresh
        def operation() -> str:
            raise cache.RefreshNeededError("Always fail")

        with pytest.raises(cache.RefreshNeededError):
            operation()

        assert cache._get_entry() is None


class TestKeyringCacheSpecific:
    """Tests specific to KeyringCache."""

    @skip_if_no_keyring
    def test_keyring_cache_persists_across_instances(self):
        fetch_count = 0

        def fetch_value() -> str:
            nonlocal fetch_count
            fetch_count += 1
            return "persistent"

        cache1 = KeyringCache(KEY_PERSIST, fetch_value)
        cache1.get_value()
        assert fetch_count == 1

        cache2 = KeyringCache(KEY_PERSIST, fetch_value)
        assert cache2.get_value() == "persistent"
        assert fetch_count == 1

    @skip_if_no_keyring
    def test_keyring_cache_custom_namespace(self):
        fetch_count = 0

        def fetch_value() -> str:
            nonlocal fetch_count
            fetch_count += 1
            return "custom-namespace-value"

        cache = KeyringCache(KEY_CUSTOM, fetch_value, namespace=KEY_NAMESPACE_CUSTOM)
        cache.get_value()
        cache.get_value()
        assert fetch_count == 1


class TestRefreshableCacheAbstract:
    """Tests for RefreshableCache abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        def fetch_value() -> str:
            return "value"

        with pytest.raises(TypeError):
            RefreshableCache("test-key", fetch_value)

    def test_refresh_needed_error_is_namespaced(self):
        def fetch_value() -> str:
            return "value"

        cache = MemoryCache("namespaced", fetch_value)

        assert hasattr(cache, "RefreshNeededError")
        assert issubclass(cache.RefreshNeededError, Exception)

        with pytest.raises(cache.RefreshNeededError):
            raise cache.RefreshNeededError("test")

    def test_cached_type_parameter_provides_type_for_lambda(self):
        # cached_type allows lambdas without return annotations
        cache = MemoryCache[str](KEY_CACHED_TYPE_TEST, lambda: "test-value", cached_type=str)
        assert cache.get_value() == "test-value"

    def test_raise_error_when_no_type_annotation_and_no_cached_type(self):
        # Should raise TypeError when fetch_fn has no return annotation
        # and cached_type is not provided
        with pytest.raises(
            TypeError,
            match="fetch_fn must have a return type annotation or cached_type must be provided",
        ):
            MemoryCache(KEY_NO_TYPE, lambda: "value")


# Keys for ChainedCache tests
KEY_CHAINED_A = TestKeyRegistry.create("chained-a")
KEY_CHAINED_B = TestKeyRegistry.create("chained-b")
KEY_CHAINED_FALLBACK = TestKeyRegistry.create("chained-fallback")


class TestChainedCache:
    """Tests for ChainedCache."""

    def test_chained_cache_reads_from_first_backend(self):
        fetch_counts = {"memory": 0, "keyring": 0}

        def fetch_memory() -> str:
            fetch_counts["memory"] += 1
            return "from-memory"

        def fetch_keyring() -> str:
            fetch_counts["keyring"] += 1
            return "from-keyring"

        # Set up memory cache with value first
        memory = MemoryCache(KEY_CHAINED_A, fetch_memory)
        memory.get_value()
        assert fetch_counts["memory"] == 1

        # Create chained cache - memory should be tried first
        cache = ChainedCache(
            backends=[MemoryCache, KeyringCache],
            key=KEY_CHAINED_A,
            fetch_fn=fetch_keyring,
        )

        result = cache.get_value()
        assert result == "from-memory"
        assert fetch_counts["keyring"] == 0  # Never called

    def test_chained_cache_falls_back_to_second_backend(self):
        fetch_count = 0

        def fetch_value() -> str:
            nonlocal fetch_count
            fetch_count += 1
            return "fallback-value"

        cache = ChainedCache(
            backends=[KeyringCache, MemoryCache],
            key=KEY_CHAINED_B,
            fetch_fn=fetch_value,
        )

        # First call - cache miss, fetches value
        result1 = cache.get_value()
        assert result1 == "fallback-value"
        assert fetch_count == 1

        # Second call - should hit memory cache
        result2 = cache.get_value()
        assert result2 == "fallback-value"
        assert fetch_count == 1

    def test_chained_cache_writes_to_first_successful_backend(self):
        fetch_count = 0

        def fetch_value() -> str:
            nonlocal fetch_count
            fetch_count += 1
            return "write-value"

        cache = ChainedCache(
            backends=[MemoryCache, KeyringCache],
            key=KEY_CHAINED_FALLBACK,
            fetch_fn=fetch_value,
        )

        cache.get_value()
        assert fetch_count == 1

        # Delete from memory to test keyring fallback
        cache._backends[0].delete()

        # Should fetch again (memory empty, keyring has it)
        cache.get_value()
        assert fetch_count == 2

    def test_chained_cache_deletes_from_all_backends(self):
        def fetch_value() -> str:
            return "delete-test"

        backends = [MemoryCache]
        if keyring_backend_available():
            backends.append(KeyringCache)

        cache = ChainedCache(
            backends=backends,
            key=TestKeyRegistry.create("chained-delete"),
            fetch_fn=fetch_value,
        )

        cache.get_value()
        cache.delete()

        # Both backends should be empty
        for backend in cache._backends:
            assert backend._get_entry() is None


# Keys for NullCache tests
KEY_NULL_A = TestKeyRegistry.create("null-a")
KEY_NULL_B = TestKeyRegistry.create("null-b")


class TestNullCache:
    """Tests for NullCache."""

    def test_null_cache_never_returns_cached_value(self):
        fetch_count = 0

        def fetch_value() -> str:
            nonlocal fetch_count
            fetch_count += 1
            return "fetched-value"

        cache = NullCache(KEY_NULL_A, fetch_value)

        # First call - fetches
        result1 = cache.get_value()
        assert result1 == "fetched-value"
        assert fetch_count == 1

        # Second call - fetches again (no caching)
        result2 = cache.get_value()
        assert result2 == "fetched-value"
        assert fetch_count == 2

    def test_null_cache_set_does_nothing(self):
        fetch_count = 0

        def fetch_value() -> str:
            nonlocal fetch_count
            fetch_count += 1
            return "value"

        cache = NullCache(KEY_NULL_B, fetch_value)

        cache.set("cached-value")
        cache.get_value()

        # Should still fetch (set did nothing)
        assert fetch_count == 1

    def test_null_cache_delete_does_nothing(self):
        fetch_count = 0

        def fetch_value() -> str:
            nonlocal fetch_count
            fetch_count += 1
            return "value"

        cache = NullCache(KEY_NULL_A, fetch_value)

        cache.delete()
        cache.get_value()

        # Should still work (delete did nothing)
        assert fetch_count == 1

    def test_null_cache_with_chained_cache(self):
        fetch_count = 0

        def fetch_value() -> str:
            nonlocal fetch_count
            fetch_count += 1
            return "chained-value"

        cache = ChainedCache(
            backends=[NullCache],
            key=TestKeyRegistry.create("null-chained"),
            fetch_fn=fetch_value,
        )

        # Should always fetch
        cache.get_value()
        assert fetch_count == 1

        cache.get_value()
        assert fetch_count == 2


class FaultyCache(RefreshableCache):
    """Faulty cache that always raises exceptions for testing."""

    def _get_entry(self):
        raise RuntimeError("Faulty backend")

    def set(self, value):
        _ = value
        raise RuntimeError("Faulty backend")

    def delete(self):
        raise RuntimeError("Faulty backend")


KEY_CHAINED_FAULTY_A = TestKeyRegistry.create("chained-faulty-a")
KEY_CHAINED_FAULTY_B = TestKeyRegistry.create("chained-faulty-b")
KEY_CHAINED_FAULTY_C = TestKeyRegistry.create("chained-faulty-c")


class TestChainedCacheFaultyBackends:
    """Tests for ChainedCache with faulty backends."""

    def test_chained_cache_continues_on_get_exception(self):
        fetch_count = 0

        def fetch_value() -> str:
            nonlocal fetch_count
            fetch_count += 1
            return "fallback-value"

        cache = ChainedCache(
            backends=[FaultyCache, MemoryCache],
            key=KEY_CHAINED_FAULTY_A,
            fetch_fn=fetch_value,
        )

        # FaultyCache raises, MemoryCache works
        result = cache.get_value()
        assert result == "fallback-value"
        assert fetch_count == 1

        # Second call should hit MemoryCache
        result2 = cache.get_value()
        assert result2 == "fallback-value"
        assert fetch_count == 1

    def test_chained_cache_continues_on_set_exception(self):
        def fetch_value() -> str:
            return "set-value"

        cache = ChainedCache(
            backends=[FaultyCache, MemoryCache],
            key=KEY_CHAINED_FAULTY_B,
            fetch_fn=fetch_value,
        )

        # FaultyCache raises on set, MemoryCache should succeed
        cache.set("test-value")

        # Value should be in MemoryCache
        entry = cache._backends[1]._get_entry()
        assert entry is not None
        assert entry.value == "test-value"

    def test_chained_cache_continues_on_delete_exception(self):
        def fetch_value() -> str:
            return "delete-value"

        cache = ChainedCache(
            backends=[FaultyCache, MemoryCache],
            key=KEY_CHAINED_FAULTY_C,
            fetch_fn=fetch_value,
        )

        cache.get_value()
        cache._backends[1].set("to-delete")

        # Delete should continue even though FaultyCache raises
        cache.delete()

        # MemoryCache should be deleted
        entry = cache._backends[1]._get_entry()
        assert entry is None
