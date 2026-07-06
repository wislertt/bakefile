# Context - RefreshableCacheRegistry

## SESSION PROGRESS

- Phases 1 and 2 complete. Phase 3 pending.

## Key Files

| File                                                                   | Role                                                                                            |
| ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `src/bakelib/refreshable_cache/cache.py`                               | `RefreshableCache` ABC + backends (`MemoryCache`, `KeyringCache`, `NullCache`, `ChainedCache`). |
| `src/bakelib/refreshable_cache/utils.py`                               | `FetchFn[T]` ABC + `RefreshNeededError`.                                                        |
| `src/bakelib/refreshable_cache/registry.py`                            | `RefreshableCacheRegistry[T]`.                                                                  |
| `src/bakelib/refreshable_cache/__init__.py`                            | Exports all public types.                                                                       |
| `src/bakelib/utils/secret.py`                                          | `SecretUtils(Bakebook)` — not yet refactored. Phase 3 pending.                                  |
| `tests/unit/bakelib/refreshable_cache/test_cache.py`                   | Cache backend tests.                                                                            |
| `tests/unit/bakelib/refreshable_cache/test_registry.py`                | Registry tests.                                                                                 |
| `tests/unit/bakelib/refreshable_cache/test_refreshable_cache_utils.py` | `FetchFn` + `SecretRegistry` integration tests.                                                 |

## Locked Decisions

1. Generic registry in `bakelib` (not secret-only).
2. Homo generic `Registry[T]`.
3. Default + override policy, plain params (no `CachePolicy` dataclass).
4. No `fetch_factory` — `register()` requires `fetch_fn` or raises. Subclasses override `register()` with domain params and resolve to `fetch_fn` before calling `super()`.
5. Manual `refresh_all` only (no scheduler).
6. Public `has_value()` on base.
7. Dup `register()` raises.

## Design

### RefreshableCacheRegistry

- Concrete class (not ABC). Subclasses override `register()` for domain-specific params.
- Class-level typed defaults: `namespace`, `ttl`, `stop`, `wait`, `cached_type` — overridable declaratively.
- `_backends: ClassVar[list[type[RefreshableCache[Any]]]]` — mutable default uses `ClassVar` + underscore; resolved to `self.backends` in `__init__`.
- `fetch_fn_cls: ClassVar[type[FetchFn[Any]] | None]` — subclasses declare their `FetchFn` subclass here.
- `__init__` params are all optional and shadow class defaults when provided.

### FetchFn

- ABC in `utils.py` (alongside `RefreshNeededError`).
- Subclasses are frozen dataclasses capturing domain params, implementing `__call__() -> T`.
- `fetch_fn` type hint everywhere: `Callable[[], T] | FetchFn[T]`.

## Key Code References

- `RefreshableCache.__init__` signature (cache.py) — registry `_build_cache` must match these kwargs.
- `ChainedCache.__init__` (cache.py) — same kwargs + `backends` list.
- `SecretUtils._get_fetch_fn` / `get_secret_cache` (secret.py) — patterns to migrate into registry subclass.

## Notes

- `MemoryCache._storage` is `ClassVar` global — isolate tests via namespace.
- `cached_type` is inferred from `fetch_fn` return annotation when not provided. Untyped lambdas require explicit `cached_type`.
