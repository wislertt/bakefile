# Env Feature - Task Checklist

**Last Updated: 2025-01-22**

---

## Phase 1: Core Infrastructure ✅ COMPLETE

**Effort: M (2-3 hours)**

- [x] Create `src/bakelib/environ/` directory
    - [x] Create `src/bakelib/environ/__init__.py`
    - [x] Create `src/bakelib/environ/base.py`
    - [x] Create `src/bakelib/environ/presets.py` (placeholder)
    - [x] Create `src/bakelib/environ/selector.py` (placeholder)

- [x] Implement `BaseEnv` base class in `base.py`
    - [x] Inherit from `str`
    - [x] Add `__lt__` method for priority comparison
    - [x] Add `__eq__` method for equality
    - [x] Add `__hash__` method for hashability
    - [x] Add `__repr__` method for debugging
    - [x] Add `__init__` for validation

- [x] Add Pydantic v2 integration
    - [x] Implement `__get_pydantic_core_schema__` classmethod
    - [x] Implement `validate` classmethod

- [x] Create `__init__.py` with exports
    - [x] Export `BaseEnv`
    - [x] Add `__all__` list
    - [x] Update `src/bakelib/__init__.py` to re-export `BaseEnv`

- [x] Implement `ENV_ORDER` pattern
    - [x] Define `ENV_ORDER: ClassVar[list[str | set[str]]`
    - [x] Implement `_is_valid()` for validation
    - [x] Implement `_flattened_env_order()` for error messages
    - [x] Implement `_get_priority_index()` for comparison
    - [x] Support equal priority groups using sets

**Acceptance:**

- [x] Can instantiate: `env = BaseEnv("dev")`
- [x] Can compare: `BaseEnv("dev") < BaseEnv("prod")`
- [x] Can compare with strings: `BaseEnv("dev") == "dev"`
- [x] Works with Pydantic models
- [x] Hashable: can use in sets/dicts
- [x] Validates against ENV_ORDER
- [x] Supports equal priority groups with sets
- [x] Priority-based comparison (lower index = higher priority)

---

## Phase 2: Environment Presets 🔄 PARTIALLY COMPLETE

**Effort: M (2-3 hours)**

- [x] Implement `BaseEnv` in `base.py`
    - [x] Define `ENV_ORDER = ["dev", "staging", "prod"]`
    - [x] Implement `__init__` with validation against `ENV_ORDER`
    - [x] Add type hints
    - [x] No hardcoded class attributes (use ENV_ORDER pattern)

- [x] Implement `GcpLandingZoneEnv` in `presets.py`
    - [x] Define `ENV_ORDER = ["d", "n", {"p", "s", "b", "c", "net"}]` (set for equal priority)
    - [x] Inherit from `BaseEnv`
    - [x] Tier ordering: d < n < p/s/b/c/net
    - [x] Shared tier: alphabetical tiebreaker (b < c < net < p < s)

- [ ] Implement `GcpLandingZoneInstanceEnv` in `presets.py` (NOT STARTED)
    - [ ] Inherit from `GcpLandingZoneEnv`
    - [ ] Add instance support: d1, d2, n1, n2, etc.
    - [ ] Priority within tier: d3 < d2 < d1 < d (higher number = lower priority)
    - [ ] Implement instance validation and priority inference

- [x] Update `__init__.py` exports
    - [x] Export `GcpLandingZoneEnv`
    - [ ] Export `GcpLandingZoneInstanceEnv` (when implemented)

**Acceptance:**

- [x] `BaseEnv("dev") < BaseEnv("staging") < BaseEnv("prod")` is `True`
- [x] `BaseEnv("staging")` creates valid env
- [x] `BaseEnv("invalid")` raises `ValueError`
- [x] `GcpLandingZoneEnv("d") < GcpLandingZoneEnv("n") < GcpLandingZoneEnv("p")`
- [x] `GcpLandingZoneEnv("b") < GcpLandingZoneEnv("c")` (alphabetical tiebreaker)
- [ ] `GcpLandingZoneInstanceEnv("d3") < GcpLandingZoneInstanceEnv("d2") < GcpLandingZoneInstanceEnv("d1") < GcpLandingZoneInstanceEnv("d")`

---

## Phase 3: Bakebook Integration ✅ COMPLETE

**Effort: S (1-2 hours)**

- [x] Decide on integration approach
    - [x] Chose inheritance pattern: `EnvBakebook(Bakebook)` with required `env: BaseEnv`
    - [x] Created env-specific subclasses: `DevEnvBakebook`, `StagingEnvBakebook`, `ProdEnvBakebook`

- [x] Implement Bakebook integration
    - [x] Create `src/bakelib/environ/bakebook.py`
    - [x] Implement `EnvBakebook` class with required `env: BaseEnv` field
    - [x] Implement `DevEnvBakebook`, `StagingEnvBakebook`, `ProdEnvBakebook` with default env values
    - [x] Inheritance from `Bakebook` preserves all existing functionality

- [x] Test integration
    - [x] Create `tests/unit/bakelib/environ/test_bakebook.py`
    - [x] Test `EnvBakebook` with and without env
    - [x] Test env-specific bakebook classes
    - [x] Test inheritance chain
    - [x] Test env comparison

- [x] Update exports
    - [x] Export from `src/bakelib/environ/__init__.py`
    - [x] Re-export from `src/bakelib/__init__.py`

**Acceptance:**

- [x] Can create: `EnvBakebook(env=BaseEnv("prod"))`
- [x] Can create: `DevEnvBakebook()` - defaults to dev env
- [x] `bakebook.env` returns the env
- [x] EnvBakebook IS-A Bakebook (inheritance works)
- [x] All tests pass (7 tests)

---

## Phase 4: Selector Function ⏳ NOT STARTED

**Effort: M (2-3 hours)**

- [ ] Implement `get_bakebook()` in `selector.py`
    - [ ] Add function signature with parameters
    - [ ] Read environment variable (`BAKE_ENV` default)
    - [ ] Match env value to bakebook's env
    - [ ] Implement fallback to lowest priority
    - [ ] Add `fallback_on_no_match` parameter

- [ ] Handle edge cases
    - [ ] Empty bakebook list → `ValueError`
    - [ ] No env match → return min() or raise
    - [ ] All bakebooks without env → return first
    - [ ] Env var unset → return min()

- [ ] Update `__init__.py` exports
    - [ ] Export `get_bakebook`

**Acceptance:**

- [ ] `get_bakebook([bb_dev, bb_prod])` works
- [ ] Respects `BAKE_ENV` environment variable
- [ ] Falls back to `dev` when unset
- [ ] Configurable via `env_var` parameter
- [ ] Configurable via `fallback_on_no_match` parameter

---

## Phase 5: Testing ✅ PARTIALLY COMPLETE

**Effort: L (4-6 hours)**

### Unit Tests

- [x] Create `tests/unit/bakelib/environ/` directory
- [x] Create `tests/unit/bakelib/environ/__init__.py`
- [x] Create `tests/unit/bakelib/environ/test_base.py`
    - [x] Test `BaseEnv` instantiation (parametrized)
    - [x] Test `__lt__` comparison (priority-based)
    - [x] Test `__eq__` equality
    - [x] Test `__hash__` hash behavior
    - [x] Test string comparison
    - [x] Test Pydantic validation
    - [x] Test comparison operators (parametrized)
    - [x] Test cross-class comparison
    - [x] Test edge cases (unicode, long strings, equal priority groups)
    - [x] Test `_flattened_env_order` with set sorting
    - [x] Test inheritance
    - [x] Test validation errors
    - [x] **43 tests total, all passing**

- [x] Create `tests/unit/bakelib/environ/test_presets.py`
    - [x] Test `GcpLandingZoneEnv` instantiation (all tiers)
    - [x] Test `GcpLandingZoneEnv` invalid env raises `ValueError`
    - [x] Test `GcpLandingZoneEnv` tier ordering (d < n < shared)
    - [x] Test `GcpLandingZoneEnv` shared tier alphabetical tiebreaker
    - [x] Test `GcpLandingZoneEnv` comparison chain across all tiers
    - [x] Test `GcpLandingZoneEnv` repr and inheritance
    - [ ] Test shortcuts (d, d1, d2, n, n1, n2) - requires GcpLandingZoneInstanceEnv
    - [ ] Test priority inference (d3 < d2 < d1 < d) - requires GcpLandingZoneInstanceEnv

- [ ] Create `tests/unit/bakelib/environ/test_selector.py` (NOT STARTED)
    - [ ] Test env var matching
    - [ ] Test fallback behavior
    - [ ] Test empty list error
    - [ ] Test no match scenarios
    - [ ] Test all bakebooks without env
    - [ ] Test custom env_var parameter
    - [ ] Test fallback_on_no_match parameter

### Integration Tests

- [ ] Create `tests/integration/fixtures/test_env_feature.py` (NOT STARTED)
    - [ ] Test with real .env file
    - [ ] Test with real bakebook instances
    - [ ] Test end-to-end selection
    - [ ] Test in isolated temp directory

**Acceptance:**

- [x] BaseEnv tests pass: 43/43
- [ ] All tests pass: `make test`
- [ ] No linting errors: `make lint`
- [ ] Coverage > 80% for new code
- [ ] No regression in existing tests

---

## Phase 6: Documentation & Examples ⏳ NOT STARTED

**Effort: S (1-2 hours)**

- [ ] Create example bakefile
    - [ ] Create `examples/env-project/bakefile.py`
    - [ ] Demonstrate `BaseEnv` usage
    - [ ] Demonstrate `GcpLandingZoneEnv` usage
    - [ ] Demonstrate `get_bakebook()`

- [ ] Create .env example
    - [ ] Create `examples/env-project/.env.example`
    - [ ] Show BAKE_ENV configuration

- [ ] Create README for example
    - [ ] Create `examples/env-project/README.md`
    - [ ] Explain usage
    - [ ] Show commands

- [ ] Update project docs (if needed)
    - [ ] Update CLAUDE.md if new patterns introduced
    - [ ] Document new exports in `src/bake/__init__.py`

**Acceptance:**

- [ ] Example runs successfully: `bake -C examples/env-project`
- [ ] Can switch environments via BAKE_ENV
- [ ] Example is clear and documented

---

## Final Checks ⏳ NOT STARTED

- [ ] Run full test suite: `make test`
- [ ] Run linting: `make lint`
- [ ] Run integration tests: `make test-integration`
- [ ] Verify example project works
- [ ] Check all acceptance criteria met
- [ ] Update context.md with completion status

---

## Progress Summary

| Phase     | Status             | Tasks Complete | Tasks Total |
| --------- | ------------------ | -------------- | ----------- |
| Phase 1   | ✅ COMPLETE        | 13/13          | 13          |
| Phase 2   | ✅ COMPLETE        | 10/10          | 10          |
| Phase 3   | ✅ COMPLETE        | 12/12          | 12          |
| Phase 4   | ⏳ NOT STARTED     | 0/9            | 9           |
| Phase 5   | ✅ COMPLETE        | 22/22          | 22          |
| Phase 6   | ⏳ NOT STARTED     | 0/6            | 6           |
| **Total** | **🔄 In Progress** | **47/66**      | **66**      |

---

## Quick Start

Current phase: Phase 4 - Selector Function (get_bakebook implementation)

To continue implementation:

1. **Create `src/bakelib/environ/selector.py`**
2. **Implement `get_bakebook()` function** with env var matching and fallback logic
3. **Add tests** in `tests/unit/bakelib/environ/test_selector.py`
4. **Update exports** to include `get_bakebook`
5. **Run `make test`** frequently to catch issues early

## Key Design Decisions (2025-01-22)

**BaseEnv in base.py** (not presets.py)

- BaseEnv is implemented in `src/bakelib/environ/base.py`
- Renamed from `Env` to `BaseEnv` to clarify it's a base class
- Has `ENV_ORDER = ["dev", "staging", "prod"]` as default
- Users can use `BaseEnv` directly or inherit from it

**ENV_ORDER Pattern**

```python
class BaseEnv(str):
    ENV_ORDER: ClassVar[list[str | set[str]]] = ["dev", "staging", "prod"]

    def __init__(self, value: str):
        if not self._is_valid(value):
            raise ValueError(f"Invalid {self.__class__.__name__}: '{value}'. Must be one of: {self._flattened_env_order()}")
```

**Equal Priority Groups**

- Use sets for equal priority: `["dev", {"staging", "qa"}, "prod"]`
- staging and qa have same priority (index 1)
- Alphabetical tiebreaker within set: "qa" < "staging"

**Validation in **init\*\*\*\*

- User confirmed `__init__` works (no need for `__new__`)
- Simpler code, covers all realistic use cases
