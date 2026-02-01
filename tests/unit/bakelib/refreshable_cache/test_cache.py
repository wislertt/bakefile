"""Unit tests for refreshable_cache module."""

import contextlib
import logging
import time
from typing import ClassVar

import keyring
import pytest

from bake.ui.logger import capsys_to_logs, has_messages_in_logs, setup_logging
from bakelib.refreshable_cache import (
    KeyringCache,
    MemoryCache,
    RefreshableCache,
)
from bakelib.refreshable_cache.cache import DEFAULT_NAMESPACE


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

    @pytest.mark.parametrize("cache_class", [MemoryCache, KeyringCache])
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

    @pytest.mark.parametrize("cache_class,ttl", [(MemoryCache, 0.01), (KeyringCache, 0.05)])
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

    @pytest.mark.parametrize("cache_class", [MemoryCache, KeyringCache])
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

    @pytest.mark.parametrize("cache_class", [MemoryCache, KeyringCache])
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

    @pytest.mark.parametrize("cache_class", [MemoryCache, KeyringCache])
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
        "cache_class",
        [MemoryCache, KeyringCache],
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
