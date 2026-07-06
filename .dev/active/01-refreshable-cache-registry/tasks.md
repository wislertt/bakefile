# Tasks - RefreshableCacheRegistry

## Phase 1: Base additions ✅

- [x] 1.1 Add public `has_value()` to `RefreshableCache` base
- [x] 1.2 Replace `_get_entry()` reaches in call sites with `has_value()`

## Phase 2: Registry ✅

- [x] 2.1 Create `RefreshableCacheRegistry[T]` with class-level defaults + `__init__`
- [x] 2.2 Implement `register()` with override-or-default resolution + dup-raise
- [x] 2.3 Implement `_build_cache()` (1 backend direct, >1 `ChainedCache`)
- [x] 2.4 Implement access: `get`, `cache`, `keys`, `is_cached`, `__contains__`
- [x] 2.5 Implement mutation: `delete`, `delete_all`, `refresh`, `refresh_all`, `unregister`
- [x] 2.6 Export from `bakelib/refreshable_cache/__init__.py`
- [x] 2.7 `FetchFn[T]` ABC + `RefreshNeededError` combined in `utils.py`
- [x] 2.8 `fetch_fn` type hints updated to `Callable[[], T] | FetchFn[T]` across all files
- [x] 2.9 Tests: `FetchFn` abstract enforcement, frozen dataclass subclasses, registry integration, `SecretRegistry` subclass pattern
- [x] 2.10 `fetch_fn_cls: ClassVar` on registry — subclasses declare their `FetchFn` class declaratively
- [x] 2.11 Rename `FetchSpec` → `FetchFn`, `fetch_spec_cls` → `fetch_fn_cls` everywhere

## Phase 3: SecretVault + SecretUtils refactor ✅

- [x] 3.1 Add `SecretVault(RefreshableCacheRegistry[str | None])` — `_backends` defaults to `[MemoryCache, KeyringCache]`, namespace `"bakebook"`, `cached_type=str`. `get_or_register()` resolves `fetch_fn` to `null_fetch_fn` when not provided.
- [x] 3.2 Refactor `SecretUtils` to delegate to `SecretVault` via lazy `vault` property. CLI surface unchanged.

## Phase 4: Tests ✅

- [x] 4.1 Unit tests for `RefreshableCacheRegistry` (complete)
- [x] 4.2 Updated `SecretUtils` tests — signature consistency test updated to compare against `RefreshableCacheRegistry.register` instead of `ChainedCache.__init__`; all 26 tests pass

## Verification

- [ ] `bake lint` clean
- [ ] `bake test` green (targeted first, full before commit)
- [ ] Import check: `from bakelib.refreshable_cache import RefreshableCacheRegistry`
- [ ] Manual smoke: `bake secret list`, `bake secret refresh`
