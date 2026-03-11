import contextlib
import logging
import sys
import time

import keyring
import pytest
from keyring.errors import NoKeyringError

from bake.ui.logger import (
    capsys_to_logs,
    has_all_messages_in_logs,
    has_message_in_logs,
    has_messages_in_logs,
    setup_logging,
)
from bakelib.refreshable_cache import (
    ChainedCache,
    KeyringCache,
    MemoryCache,
    NullCache,
    RefreshableCache,
)
from tests.utils.misc import flaky_on_windows_ci


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


def cleanup_keyring_keys(keys: list[tuple[str, str]]) -> None:
    for service, username in keys:
        with contextlib.suppress(Exception):
            keyring.delete_password(service, username)


# Test key constants
KEY_BASE = "test-cache-base"
KEY_TTL = "test-cache-ttl"
KEY_NO_TTL = "test-cache-no-ttl"
KEY_NO_ERROR = "test-cache-no-error"
KEY_DECORATOR = "test-cache-decorator"
KEY_DELETE = "test-cache-delete"
KEY_DECORATOR_ONCE = "test-cache-once"
KEY_DECORATOR_CACHE_DELETE = "test-cache-cache-delete"
KEY_PERSIST = "test-cache-persist"
KEY_CACHED_TYPE_TEST = "test-cache-cached-type-test"
KEY_NO_TYPE = "test-cache-no-type"
KEY_A = "test-cache-a"
KEY_B = "test-cache-b"

# Keyring namespace constants
KEY_NAMESPACE_CUSTOM = "my-app"
KEY_CUSTOM = "test-custom"


# Keys for ChainedCache tests
KEY_CHAINED_A = "test-chained-a"
KEY_CHAINED_B = "test-chained-b"
KEY_CHAINED_FALLBACK = "test-chained-fallback"


# Keys for NullCache tests
KEY_NULL_A = "test-null-a"
KEY_NULL_B = "test-null-b"


# Keys for faulty backend tests
KEY_CHAINED_FAULTY_A = "test-chained-faulty-a"
KEY_CHAINED_FAULTY_B = "test-chained-faulty-b"
KEY_CHAINED_FAULTY_C = "test-chained-faulty-c"


class TestCacheBasics:
    """Tests for basic cache functionality."""

    @pytest.mark.parametrize(
        "cache_class", [MemoryCache] + ([KeyringCache] if keyring_backend_available() else [])
    )
    def test_cache_stores_and_retrieves_value(self, cache_class: type[RefreshableCache]):
        # Ensure clean state for KeyringCache
        if cache_class == KeyringCache:
            cleanup_keyring_keys([("bakelib.refreshable_cache", KEY_BASE)])

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
        "cache_class, ttl",
        [(MemoryCache, 0.01)] + ([(KeyringCache, 0.2)] if keyring_backend_available() else []),
    )
    @flaky_on_windows_ci()
    def test_cache_respects_ttl(
        self, cache_class: type[RefreshableCache], ttl: float, capsys: pytest.CaptureFixture[str]
    ):
        setup_logging(
            level_per_module={"": logging.WARNING, "bakelib": logging.DEBUG}, is_pretty_log=False
        )

        # Ensure clean state - delete any existing entry from previous test runs
        if cache_class == KeyringCache:
            cleanup_keyring_keys([("bakelib.refreshable_cache", KEY_TTL)])

        fetch_count = {"count": 0}

        def fetch_value() -> str:
            fetch_count["count"] += 1
            return "test-value"

        cache = cache_class(KEY_TTL, fetch_value, ttl=ttl)
        _ = capsys.readouterr()

        # First call - should fetch
        result1 = cache.get_value()
        assert result1 == "test-value"
        assert fetch_count["count"] == 1

        # Second call - should hit cache
        result2 = cache.get_value()
        assert result2 == "test-value"
        assert fetch_count["count"] == 1

        # Verify log messages (order-independent for Windows compatibility)
        logs = capsys_to_logs(capsys)
        assert has_all_messages_in_logs(logs, ["Cache miss", "Fetching value", "Cache hit"])

        # Use larger buffer on Windows due to timing precision issues
        buffer = 2 if sys.platform == "win32" else 0.1
        time.sleep(ttl + buffer)

        # Third call - should refetch after TTL expires
        result3 = cache.get_value()
        assert result3 == "test-value"
        assert fetch_count["count"] == 2

        # Verify cache expired message
        logs = capsys_to_logs(capsys)
        assert has_message_in_logs(logs, "Cache expired")

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
        # Ensure clean state for KeyringCache
        if cache_class == KeyringCache:
            cleanup_keyring_keys([("bakelib.refreshable_cache", KEY_DECORATOR)])

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
        # Ensure clean state for KeyringCache
        if cache_class == KeyringCache:
            cleanup_keyring_keys([("bakelib.refreshable_cache", KEY_NO_ERROR)])

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
        """KeyringCache persists across instances (singleton-like storage via system keyring)."""
        # Ensure clean state before test
        cleanup_keyring_keys([("bakelib.refreshable_cache", KEY_PERSIST)])

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


class TestMemoryCacheSpecific:
    """Tests specific to MemoryCache."""

    def test_memory_cache_persists_across_instances(self):
        """MemoryCache persists across instances (singleton-like storage via class variable)."""
        fetch_count = 0

        def fetch_value() -> str:
            nonlocal fetch_count
            fetch_count += 1
            return "persistent"

        cache1 = MemoryCache(KEY_PERSIST, fetch_value)
        cache1.get_value()
        assert fetch_count == 1

        cache2 = MemoryCache(KEY_PERSIST, fetch_value)
        assert cache2.get_value() == "persistent"
        assert fetch_count == 1  # No re-fetch, same storage


class TestKeyringCacheSpecificMore:
    """More tests specific to KeyringCache."""

    @skip_if_no_keyring
    def test_keyring_cache_custom_namespace(self):
        # Ensure clean state before test
        cleanup_keyring_keys([(KEY_NAMESPACE_CUSTOM, KEY_CUSTOM)])

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
KEY_CHAINED_A = "test-chained-a"
KEY_CHAINED_B = "test-chained-b"
KEY_CHAINED_FALLBACK = "test-chained-fallback"


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

        backends: list[type[RefreshableCache[str]]] = [KeyringCache, MemoryCache]
        cache = ChainedCache(
            backends=backends,
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

        backends: list[type[RefreshableCache[str]]] = [MemoryCache, KeyringCache]
        cache = ChainedCache(
            backends=backends,
            key=KEY_CHAINED_FALLBACK,
            fetch_fn=fetch_value,
        )

        cache.get_value()
        assert fetch_count == 1

        # Delete from memory to test keyring fallback
        cache._backends[0].delete()

        # Should fetch again (memory empty, keyring has it)
        cache.get_value()
        # If keyring backend is available, value was persisted in keyring (fetch_count == 1)
        # If no keyring backend, value was lost, so we fetch again (fetch_count == 2)
        expected_fetch = 1 if keyring_backend_available() else 2
        assert fetch_count == expected_fetch

    def test_chained_cache_deletes_from_all_backends(self):
        def fetch_value() -> str:
            return "delete-test"

        backends: list[type[RefreshableCache[str]]] = [MemoryCache]
        if keyring_backend_available():
            backends.append(KeyringCache)

        cache = ChainedCache(
            backends=backends,
            key="test-chained-delete",
            fetch_fn=fetch_value,
        )

        cache.get_value()
        cache.delete()

        # Both backends should be empty
        for backend in cache._backends:
            assert backend._get_entry() is None

    def test_chained_cache_sets_to_all_backends(self):
        def fetch_value() -> str:
            return "default"

        backends: list[type[RefreshableCache[str]]] = [MemoryCache]
        if keyring_backend_available():
            backends.append(KeyringCache)

        cache = ChainedCache(
            backends=backends,
            key="test-chained-set-all",
            fetch_fn=fetch_value,
        )

        cache.set("written-to-all")

        # All backends should have the value
        for backend in cache._backends:
            entry = backend._get_entry()
            assert entry is not None
            assert entry.value == "written-to-all"


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

        backends: list[type[RefreshableCache[str]]] = [NullCache]
        cache = ChainedCache(
            backends=backends,
            key="test-null-chained",
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


class TestChainedCacheFaultyBackends:
    """Tests for ChainedCache with faulty backends."""

    def test_chained_cache_continues_on_get_exception(self):
        fetch_count = 0

        def fetch_value() -> str:
            nonlocal fetch_count
            fetch_count += 1
            return "fallback-value"

        backends: list[type[RefreshableCache[str]]] = [FaultyCache, MemoryCache]
        cache = ChainedCache(
            backends=backends,
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

        backends: list[type[RefreshableCache[str]]] = [FaultyCache, MemoryCache]
        cache = ChainedCache(
            backends=backends,
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

        backends: list[type[RefreshableCache[str]]] = [FaultyCache, MemoryCache]
        cache = ChainedCache(
            backends=backends,
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

    def test_chained_cache_all_backends_fail_on_set(self):
        def fetch_value() -> str:
            return "all-fail-value"

        backends: list[type[RefreshableCache[str]]] = [FaultyCache, FaultyCache]
        cache = ChainedCache(
            backends=backends,
            key="test-chained-all-fail",
            fetch_fn=fetch_value,
        )

        # All backends fail - should log and complete without error
        cache.set("test-value")
