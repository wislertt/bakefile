# Registry Axis Clarity - Implementation Plan

## Executive Summary

`RefreshableCacheRegistry` mixes two independent concerns under ambiguous verbs:
**handle** operations (registration entries in `self._caches`) and **value**
operations (cached data inside a handle). Method names cross the two axes, so
`delete` vs `unregister` and `get` vs `get_or_register` force readers to guess.

Goal: rename the **handle** axis to a repository-pattern `*_cache` family
(`insert_cache` / `ensure_cache` / `upsert_cache` / `remove_cache` / `get_cache`
/ `list_cache_keys`), rename value-axis `cache.get_value`→`get` and
`is_cached`→`has_value`, add the missing value writer `set`, group methods by
axis, and simplify callers that hand-roll the upsert pattern.

No behavior change. Pure rename + reorder + one additive method + caller cleanup.

## Background: Two Axes

Every operation acts on exactly one of:

- **Handle** — the `RefreshableCache` registered under a key in `self._caches`.
- **Value** — the cached data held inside a handle (`RefreshableCache.get()`).

`unregister` is the only method that touches both (pops handle + clears value).
Everything else is single-axis. Naming must make the axis obvious.

## Current State

`src/bakelib/refreshable_cache/registry.py` method inventory, mapped to axis:

| Method            | Axis                  | Behavior                                      |
| ----------------- | --------------------- | --------------------------------------------- |
| `register`        | handle create         | add entry; ValueError if present              |
| `get_or_register` | handle create         | register-if-absent                            |
| `upsert`          | handle create/replace | unregister-if-present + register (just added) |
| `unregister`      | handle+value delete   | pop entry + `cache.delete()`                  |
| `cache(key)`      | handle read           | return `RefreshableCache`; KeyError if absent |
| `__contains__`    | handle read           | entry present?                                |
| `keys()`          | handle read           | entry keys                                    |
| `get(key)`        | value read            | `cache(key).get_value()`                      |
| `delete(key)`     | value delete          | `cache(key).delete()`; handle kept            |
| `delete_all()`    | value delete          | clear all values; handles kept                |
| `refresh(key)`    | value refresh         | `cache(key).refresh()`                        |
| `refresh_all()`   | value refresh         | refresh every value                           |
| `is_cached(key)`  | value status          | handle exists AND `has_value()`               |

### Confusion Points

- `delete` vs `unregister` — both sound like removal; one is value-only, one is
  handle+value. **Worst offender.**
- `delete_all()` — sounds like wipe registry; actually clears values, keeps
  handles.
- `get(key)` (value read) vs `get_or_register` (handle create) — overloaded "get".
- `get(key)` (value) vs `cache(key)` (handle) — both reads, unclear which.
- `is_cached` checks value, but reads like a handle query.

### cache.py value surface (parity reference)

`RefreshableCache` (the handle) uses value verbs `get_value`, `set`, `delete`,
`refresh`, `has_value`. After this plan, `get_value`→`get`; the rest stand.
Registry value-axis methods mirror these.

## Caller Scope (grep results)

**Handle-axis src callers:**

- `register` → `secret.py:36`, `space/lib.py:67`
- `unregister` → `space/lib.py:66`
- `cache(key)` → `secret.py:62,65,68,71`, `space/lib.py:73`
- `keys()` → `secret.py:50,55`
- `is_cached` → `secret.py:57`

**Value-axis src callers:**

- `delete_all` → `secret.py:108`
- `refresh_all` → `secret.py:124`
- `get`, `delete`, `refresh` (single-key) → **0 src callers** (tests only)

### Key findings

1. Single-key value wrappers (`get`/`delete`/`refresh`) have **zero src
   callers** — `secret.py` bypasses them via `cache(key).get_value()` etc.
   Renaming these touches tests only.
2. `space/lib.py:66-67` hand-rolls upsert:
    ```python
    vault.unregister(key)
    vault.register(key, ...)
    ```
    → collapse to `vault.upsert(key, ...)`.
3. `secret.py:65` bypasses a value writer: `cache(key).set(value)`. Registry has
   no `set`, so this is forced. Add one.

## Proposed Future State

### Naming

**Selected path: repository-pattern `*_cache` family for the handle axis.**
`RefreshableCacheRegistry` is a repository of `RefreshableCache` objects; repo
methods name their entity (`UserRepository.get_user` →
`CacheRegistry.get_cache`). The value axis keeps bare verbs. Two clean
vocabularies result: `cache` noun = handle op, bare verb = value op.

**Handle axis — renames (repo family, all `*_cache`):**

- `register` → `insert_cache`. Strict create; errors if key present. `insert` =
  CRUD strict-add.
- `get_or_register` → `ensure_cache`. Create-if-absent, return existing. `ensure`
  = "ensure registered, return it".
- `upsert` → `upsert_cache`. Create-or-replace; always fresh.
- `unregister` → `remove_cache`. Delete handle + clear value.
- `cache(key)` → `get_cache(key)`. Read one; returns the `RefreshableCache`. Name
  matches the return type.
- `keys()` → `list_cache_keys()`. Read all; verb form matches siblings.
- `__contains__` — kept (powers `key in registry`; Python protocol).

**Value axis — renames:**

- `cache.get_value` → `cache.get` (in `cache.py`). Conventional; parity with
  `registry.get`.
- `is_cached` → `has_value`. Parity with `cache.has_value()`; removes the
  `cache` word from the value axis so `cache` belongs only to handle ops.

**Value axis — addition:**

- `set(key, value)` (new). Value write; parity with `cache.set`. Replaces the
  forced `get_cache(key).set(value)` bypass at `secret.py:65`.

**Value axis — kept:**

- `get(key)` — delegates `cache.get`.
- `delete`, `delete_all` — parity with `cache.delete`.
- `refresh`, `refresh_all`.

**Verb choices:**

- `insert` / `upsert` pair — `insert` strict (fails if exists), `upsert`
  insert-or-replace. Standard, distinct semantics.
- `ensure` — Pythonic create-if-absent.
- `cache` noun (not `entry`) — truthful (`self._caches` holds `RefreshableCache`
  objects, built at registration) + repository-pattern entity naming. `entry`
  is generic; `cache` names the return type.
- `has_value` over `is_cached` — separates `cache` (handle) from `value` axes.

**cache.py touched.** `get_value` → `get` (1 abstract + 3 impls).
`set`/`delete`/`refresh`/`has_value` unchanged.

### File Arrangement

Group by axis; stop stranding the delete at the bottom:

```python
# ── Handle (cache repo) ──
insert_cache         # was register
ensure_cache         # was get_or_register
upsert_cache         # was upsert
remove_cache         # was unregister
get_cache            # was cache
list_cache_keys      # was keys
__contains__

# ── Value ──
get                  # delegates cache.get
set                  # new
delete
delete_all
refresh
refresh_all
has_value            # was is_cached

# ── Internal ──
_build_cache
```

cache.py: `get_value` → `get` (1 abstract + 3 impls). Rest unchanged.

## Implementation Phases

### Phase 1: cache.py `get_value` → `get` (foundational)

Registry value methods delegate to `cache.get`, so rename the cache method first.

- [ ] 1.1 Rename `get_value` → `get` in `cache.py`: abstract def + MemoryCache,
      KeyringCache, ChainedCache impls. Bodies unchanged.
- [ ] 1.2 Update src callers of `.get_value()`: `registry.py`, `secret.py:62`,
      `space/lib.py:111`.
- [ ] 1.3 Update test callers (~51 sites): `test_cache.py`, `test_registry.py`,
      `tests/unit/bakelib/space/test_lib.py`.
      Acceptance: `uv run pytest tests/unit/bakelib/refreshable_cache/` green.

### Phase 2: Registry handle-axis rename (repo family)

- [ ] 2.1 Rename handle methods: `register`→`insert_cache`,
      `get_or_register`→`ensure_cache`, `upsert`→`upsert_cache`,
      `unregister`→`remove_cache`, `cache`→`get_cache`, `keys`→`list_cache_keys`.
      Keep `__contains__`.
- [ ] 2.2 Reorder by axis (handle → value → internal). `_build_cache` last.
- [ ] 2.3 Update `test_registry.py` call sites; fix `_KeyRegistry` subclass
      override (`register`→`insert_cache`).
      Acceptance: `uv run pytest tests/unit/bakelib/refreshable_cache/test_registry.py`
      green.

### Phase 3: Registry value-axis rename + add

- [ ] 3.1 Rename `is_cached` → `has_value`.
- [ ] 3.2 Add `set(self, key: str, value: T) -> None` delegating to
      `get_cache(key).set(value)`.
- [ ] 3.3 Update `test_registry.py`: `is_cached`→`has_value` call sites; add
      `set` and `has_value` tests.
      Acceptance: registry tests green.

### Phase 4: Caller simplification

- [ ] 4.1 `secret.py`: `register`→`insert_cache` (36); `get_or_register` /
      `keys` / `is_cached` (50, 55, 57) → `ensure_cache` / `list_cache_keys` /
      `has_value`; `cache(key)`→`get_cache(key)` (62, 65, 68, 71);
      `cache(key).set(value)`→`set(key, value)` (65). (`delete_all` at 108 kept.)
- [ ] 4.2 `space/lib.py`: `unregister` + `register` → `upsert_cache` (66-67);
      `cache(key)`→`get_cache(key)` (73); `get_value`→`get` (111).
      Acceptance: behavior identical (old handle cleaned, new registered).
- [ ] 4.3 Run targeted tests for touched modules; full `bake test` before commit.

### Phase 5: Verify

- [ ] 5.1 `bake lint` clean.
- [ ] 5.2 `bake test` green.
- [ ] 5.3 Grep confirms no stale references remain: `get_value`, `register(`,
      `get_or_register`, `unregister(`, `upsert(`, `.cache(`, `is_cached`,
      `.keys()`.

## Blast Radius

- `src/bakelib/refreshable_cache/cache.py` — `get_value` → `get` (1 abstract + 3 impls).
- `src/bakelib/refreshable_cache/registry.py` — full handle-axis repo rename
  (6 methods), `is_cached`→`has_value`, +`set`, reorder.
- `src/bakelib/utils/secret.py` — `register`/`get_or_register`/`keys`/`is_cached`/
  `cache`/`delete_all` call sites (lines 36, 50, 55, 57, 62, 65, 68, 71, 108).
- `src/bakelib/space/lib.py` — `unregister`+`register`→`upsert_cache`,
  `cache`→`get_cache`, `get_value`→`get` (66, 67, 73, 111).
- `tests/unit/bakelib/refreshable_cache/test_cache.py` — ~48 `get_value` sites.
- `tests/unit/bakelib/refreshable_cache/test_registry.py` — bulk rename
  (all handle methods + `is_cached`), `_KeyRegistry` subclass, +tests.
- `tests/unit/bakelib/space/test_lib.py` — `get_value` site.

Public API impact: `RefreshableCacheRegistry` and `RefreshableCache` are exported
(`__init__.py`). This rename **breaks merged methods** `register` /
`get_or_register` / `unregister` (PRs #105 / #108 / #109) plus the uncommitted
`upsert`. Bigger break than prior options, but src has no external consumers.
Acceptable on a small repo — pay once for a clean, self-documenting API.

## Risks

- **Subclass overrides.** Test fixture `_KeyRegistry` overrides `register` → must
  rename to `insert_cache`. `SecretUtilsKeyringCacheRegistry` does not override
  the renamed methods. Low risk.
- **Merged-API break.** `register` / `get_or_register` / `unregister` ship in
  merged PRs (#105 / #108 / #109). Renaming breaks their public surface.
  Internal repo, acceptable — note in commit/PR description.
- **`get_value` rename breadth.** ~51 test sites; mechanical but easy to miss
  one. Phase 5.3 grep guards against stale references.
- **`upsert_cache` kwargs filtering.** `space/lib.py` collapse must preserve
  whatever kwargs it passes to `register`. Verify before/after parity.
- **Name collisions.** No existing `insert_cache` / `ensure_cache` /
  `upsert_cache` / `remove_cache` / `get_cache` / `list_cache_keys` / `has_value`
  symbols on the registry. Safe.

## Resolved Decisions

1. **Handle-axis term: `cache`, not `entry`.** Truthful (`self._caches` holds
   `RefreshableCache` objects) + repository-pattern entity naming.
2. **Handle family: `*_cache` repo verbs** — `insert_cache` / `ensure_cache` /
   `upsert_cache` / `remove_cache` / `get_cache` / `list_cache_keys`.
3. **`cache.py`: `get_value` → `get`** for conventional parity.
4. **`is_cached` → `has_value`: YES** (was deferred). Separates `cache` (handle)
   from `value` axes; parity with `cache.has_value`.
5. **`delete` / `delete_all` → `invalidate`: NO** — kept for `cache.delete` parity.
6. **Dict protocol:** keep `__contains__` (powers `in`); `keys()` →
   `list_cache_keys` for verb consistency with the repo family.
