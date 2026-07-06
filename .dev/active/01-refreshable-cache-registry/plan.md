# RefreshableCacheRegistry - Implementation Plan

## Executive Summary

Add `RefreshableCacheRegistry` to `bakelib`: a generic container that owns many `RefreshableCache` instances sharing a namespace + default policy. Supports list/get/delete/refresh_all + per-entry policy override. Then refactor `SecretUtils` (bake) to delegate to a thin `SecretVault(RefreshableCacheRegistry[str])` subclass.

## Motivation

Today two projects hand-roll the same pattern:

- `bake` → `SecretUtils`: tracks secret keys, builds `ChainedCache` per key, has list/get/set/del/refresh (incl. bulk). Tied to "secret" + Bakebook CLI.
- `abc-infra-tester` → `SecretRotationPolicy`: policy/factory dataclass, `build_cache()` per secret. No registry.

Both = **Registry + Policy + Factory** blurred. Extract once into `bakelib`, reuse everywhere.

## Current State

- `src/bakelib/refreshable_cache/cache.py` — `RefreshableCache` ABC (single-key), backends: `MemoryCache`, `KeyringCache`, `NullCache`, `ChainedCache`. Ops: `get_value`, `set`, `delete`, `refresh`, `catch_refresh`, `acatch_refresh`, `has_value`.
- `src/bakelib/refreshable_cache/utils.py` — `FetchFn[T]` ABC + `RefreshNeededError`.
- `src/bakelib/refreshable_cache/registry.py` — `RefreshableCacheRegistry[T]` implemented.
- `src/bakelib/utils/secret.py` — `SecretUtils(Bakebook)`: still hand-rolls `ChainedCache` per key. Phase 3 pending.

## Implemented State

```
bakelib/refreshable_cache/
  cache.py      # base + backends
  utils.py      # FetchFn[T] ABC + RefreshNeededError
  registry.py   # RefreshableCacheRegistry[T]
  __init__.py   # exports all public types
bake/utils/secret.py
  SecretUtils   # pending refactor (Phase 3)
```

## Decisions (locked)

1. **Generic registry**, not secret-only. `RefreshableCacheRegistry[T]` in `bakelib`. `SecretVault` thin subclass in `bake`.
2. **Homo generic typing** — one `T` per registry instance. Secret domain = `str`.
3. **Default + override policy** — registry holds class-level defaults (`ttl`, `stop`, `wait`, `backends`, `cached_type`); `register()` accepts per-entry overrides. `None` sentinel = inherit default. Resolved + frozen at `register()` time.
4. **No `CachePolicy` dataclass** — plain params.
5. **No `fetch_factory`** — `register()` requires `fetch_fn` or raises. Subclasses override `register()` with domain params, resolve to `fetch_fn`, call `super().register(fetch_fn=...)`.
6. **`FetchFn[T]` ABC** — structured callable. Subclasses are frozen dataclasses. `fetch_fn` type hint: `Callable[[], T] | FetchFn[T]`.
7. **`fetch_fn_cls: ClassVar`** — subclasses declare their `FetchFn` subclass declaratively.
8. **Manual `refresh_all` only** — no background scheduler.
9. **Public `has_value()`** on `RefreshableCache` base.
10. **Duplicate `register()` raises** — force explicit `unregister()` then `register()`.

## Implementation Phases

### Phase 1: Base additions (`cache.py`) ✅

- Task 1.1: Add public `has_value()` to `RefreshableCache` base.
- Task 1.2: Replace `_get_entry()` reaches in call sites with `has_value()`.

### Phase 2: Registry (`registry.py`) ✅

- Task 2.1: `RefreshableCacheRegistry[T]` with class-level defaults + `__init__`.
- Task 2.2: `register()` with override-or-default resolution + dup-raise.
- Task 2.3: `_build_cache()` (1 backend direct, >1 `ChainedCache`).
- Task 2.4: Access ops: `get`, `cache`, `keys`, `is_cached`, `__contains__`.
- Task 2.5: Mutation ops: `delete`, `delete_all`, `refresh`, `refresh_all`, `unregister`.
- Task 2.6: Export from `__init__.py`.
- Task 2.7: `FetchFn[T]` ABC in `utils.py` (with `RefreshNeededError`).
- Task 2.8: `fetch_fn` type hints updated to `Callable[[], T] | FetchFn[T]` across all files.
- Task 2.9: Tests for `FetchFn` + `SecretRegistry` integration.

### Phase 3: SecretVault + SecretUtils refactor (`bake`)

- Task 3.1: Add `SecretVault(RefreshableCacheRegistry[str])` thin subclass — namespace `"bakebook"`, backends `[MemoryCache, KeyringCache]`, `cached_type=str`.
- Task 3.2: Refactor `SecretUtils` to delegate to `SecretVault`. CLI surface unchanged.

### Phase 4: Tests

- Task 4.1: ✅ Unit tests for `RefreshableCacheRegistry` (complete).
- Task 4.2: Update `SecretUtils` tests for delegation; existing tests still pass.

## Risk Assessment

- **`MemoryCache._storage` is `ClassVar` global dict** — tests isolate via namespace.
- **`cached_type` inference** — when `cached_type=None` and `fetch_fn` lacks return annotation, base raises `TypeError`. Untyped lambdas require explicit `cached_type`.
- **`SecretUtils` backward compat** — public CLI surface must not change. Internal refactor only.

## Out of Scope

- Background auto-refresh scheduler.
- Parallel/concurrent `refresh_all`.
- Heterogeneous typing (`Registry[Any]`).
- `CachePolicy` dataclass extraction.
- Refactoring `abc-infra-tester` `SecretRotationPolicy`.
