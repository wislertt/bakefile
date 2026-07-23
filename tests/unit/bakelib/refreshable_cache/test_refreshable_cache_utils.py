from dataclasses import dataclass

import pytest

from bakelib.refreshable_cache import (
    FetchFn,
    MemoryCache,
    RefreshableCacheRegistry,
)


@dataclass(frozen=True)
class SecretFetch(FetchFn[str]):
    project_id: str
    secret_id: str

    def __call__(self) -> str:
        return f"{self.project_id}/{self.secret_id}"


@dataclass(frozen=True)
class CountedFetch(FetchFn[int]):
    multiplier: int

    def __call__(self) -> int:
        return self.multiplier * 10


class TestFetchFnAbstract:
    def test_base_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            FetchFn(key="k")  # type: ignore[abstract]

    def test_subclass_without_call_cannot_be_instantiated(self):
        class Bad(FetchFn[str]):
            pass

        with pytest.raises(TypeError):
            Bad(key="k")  # type: ignore[abstract]


class TestSecretFetchDummy:
    def test_call_returns_formatted(self):
        spec = SecretFetch(key="k", project_id="p1", secret_id="db")
        assert spec() == "p1/db"

    def test_fields_typed(self):
        spec = SecretFetch(key="k", project_id="p1", secret_id="db")
        assert spec.project_id == "p1"
        assert spec.secret_id == "db"

    def test_reusable_across_calls(self):
        spec = SecretFetch(key="k", project_id="p1", secret_id="db")
        assert spec() == "p1/db"
        assert spec() == "p1/db"

    def test_distinct_instances_independent(self):
        a = SecretFetch(key="k", project_id="p1", secret_id="db")
        b = SecretFetch(key="k", project_id="p2", secret_id="api")
        assert a() == "p1/db"
        assert b() == "p2/api"


class TestFetchSpecDifferentT:
    def test_int_fetch_spec(self):
        spec = CountedFetch(key="k", multiplier=5)
        assert spec() == 50


class TestFetchSpecAsRegistryOverride:
    def test_fetch_spec_used_as_fetch_fn_override(self):
        registry = RefreshableCacheRegistry(
            namespace="reg-spec-override", backends=[MemoryCache], cached_type=str
        )
        registry.insert_cache("db", fetch_fn=SecretFetch(key="db", project_id="p1", secret_id="db"))
        assert registry.get("db") == "p1/db"

    def test_same_fetcher_different_params_per_entry(self):
        registry = RefreshableCacheRegistry(
            namespace="reg-spec-multi", backends=[MemoryCache], cached_type=str
        )
        registry.insert_cache("db", fetch_fn=SecretFetch("db", "p1", "db"))
        registry.insert_cache("api", fetch_fn=SecretFetch("api", "p1", "api"))
        registry.insert_cache("tok", fetch_fn=SecretFetch("tok", "p2", "tok"))

        assert registry.get("db") == "p1/db"
        assert registry.get("api") == "p1/api"
        assert registry.get("tok") == "p2/tok"

    def test_fetch_spec_with_int_t(self):
        registry = RefreshableCacheRegistry(
            namespace="reg-spec-int", backends=[MemoryCache], cached_type=int
        )
        registry.insert_cache("count", fetch_fn=CountedFetch(key="count", multiplier=7))
        assert registry.get("count") == 70

    def test_fetch_spec_works_with_refresh(self):
        calls: list[int] = []

        @dataclass(frozen=True)
        class CountingFetch(FetchFn[str]):
            name: str

            def __call__(self) -> str:
                calls.append(1)
                return f"v{len(calls)}-{self.name}"

        registry = RefreshableCacheRegistry(
            namespace="reg-spec-refresh", backends=[MemoryCache], cached_type=str
        )
        registry.insert_cache("k", fetch_fn=CountingFetch(key="k", name="k"))
        assert registry.get("k") == "v1-k"
        assert registry.refresh("k") == "v2-k"
