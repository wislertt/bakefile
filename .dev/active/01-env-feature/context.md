# Env Feature - Context

**Last Updated: 2025-01-22**

---

## SESSION PROGRESS (2025-01-22)

### ✅ COMPLETED (Phase 1 + Additional)

- Initial planning phase complete
- Dev docs structure created (plan, context, tasks files)
- Codebase exploration completed
- Design decisions agreed upon with user
- **Phase 1: Core Infrastructure** (2025-01-21)
    - Created `src/bakelib/environ/` directory structure
    - Implemented `Env` base class in `base.py`
    - Added comparison operators (`__lt__`, `__eq__`, `__hash__`)
    - Added Pydantic v2 integration
    - Created `__init__.py` with exports
    - Verified basic functionality with test script
- **Phase 2: BaseEnv Implementation** (2025-01-22)
    - Renamed `Env` → `BaseEnv` (base class with default ENV_ORDER)
    - Implemented `ENV_ORDER` pattern with `list[str | set[str]]` type
    - Added validation in `__init__` (user confirmed `__init__` works for their use case)
    - Implemented priority-based comparison (index-based, lower = higher priority)
    - Added support for equal priority groups using sets
    - Implemented `_is_valid()`, `_flattened_env_order()`, `_get_priority_index()` helpers
    - Created comprehensive test suite (43 tests, all passing)
    - Used `@pytest.mark.parametrize` for test simplification
    - Tests cover: validation, comparison, equality, hash, repr, Pydantic integration, inheritance, edge cases

### 🟡 IN PROGRESS

- None - Phase 2 (BaseEnv) is complete, awaiting user direction on next phase

### ⏳ NOT STARTED

- Phases 3-6 (Bakebook integration, selector, testing, documentation)

---

## Key Design Decisions (Updated 2025-01-22)

### 1. Naming Convention

**Components:**

- Base class: `BaseEnv` (not `Env` - to avoid confusion, `BaseEnv` is the base class with defaults)
- Universal preset: Uses `BaseEnv` directly (dev/staging/prod - 3-tier)
- GCP Landing Zone preset: `GcpLandingZoneEnv` (d/n/p/s/b/c/net)
- GCP Landing Zone instances: `GcpLandingZoneInstanceEnv` (d1, d2, n1, n2, etc.)
- Selector function: `get_bakebook([bb_dev, bb_prod])`

**Rationale:**

- `BaseEnv` is a base class with sensible defaults (dev/staging/prod)
- Users can use `BaseEnv` directly or inherit from it
- `BaseEnv` serves as base class for custom environments
- Renamed from `Env` to `BaseEnv` to clarify its role as a base class

### 2. ENV_ORDER Pattern (Updated 2025-01-22)

**Type:** `list[str | set[str]]` (not `list[str] | set[str]`)

**Structure:**

```python
class BaseEnv(str):
    ENV_ORDER: ClassVar[list[str | set[str]]] = ["dev", "staging", "prod"]

    def __init__(self, value: str):
        if not self._is_valid(value):
            raise ValueError(f"Invalid {self.__class__.__name__}: '{value}'. Must be one of: {self._flattened_env_order()}")
```

**Key Changes:**

- **Uses `set` for equal priority groups** (not `list` within list)
- Example: `["dev", {"staging", "qa"}, "prod"]`
    - "dev" has highest priority (index 0)
    - "staging" and "qa" have equal priority (both in set at index 1)
    - "prod" has lowest priority (index 2)
- **Comparison is priority-based** (not alphabetical)
    - Lower index = higher priority
    - Same priority group uses alphabetical as tiebreaker

### 3. Validation Approach

**Decision:** Use `__init__` (not `__new__`) for validation

**Rationale:**

- User confirmed `__init__` works for their use case
- Simpler code, easier to understand
- Covers all realistic use cases (Pydantic integration, normal instantiation)
- The `__new__` bypass scenario is edge-case/academic (requires deliberate `str.__new__()` call)

### 4. Code Simplification

**Test Simplification:**

- Used `@pytest.mark.parametrize` to combine repetitive tests
- Reduced test count from 52 to 43 through parametrization
- Removed redundant tests and `TestBaseEnvInitVsNew` (non-issue)
- Added `test_env_order_with_sets_and_strings` for equal priority groups
- Added `test_flattened_env_order_sorts_set_items` to test set sorting

**Files Modified:**

- `src/bakelib/environ/base.py` - Complete `BaseEnv` implementation
- `src/bakelib/environ/__init__.py` - Exports `BaseEnv`
- `src/bakelib/__init__.py` - Re-exports `BaseEnv`
- `tests/unit/bakelib/environ/test_base.py` - 43 comprehensive tests

---

## Key Design Decisions (From Previous Session)

### Naming Convention

**Components:**

- Base class: `BaseEnv` (not `Environment` - more concise)
- Universal preset: `BaseEnv` (dev/staging/prod - 3-tier)
- GCP Landing Zone preset: `GcpLandingZoneEnv` (d/n/p/s/b/c/net)
- GCP Landing Zone instances: `GcpLandingZoneInstanceEnv` (d1, d2, n1, n2, etc.)
- Selector function: `get_bakebook([bb_dev, bb_prod])`

**Rationale:**

- `BaseEnv` is a base class with common defaults
- `BaseEnv` is universal - users can ignore staging for 2-tier use
- `GcpLandingZoneEnv` follows GCP Landing Zone documentation exactly
- `GcpLandingZoneInstanceEnv` adds instance support as separate class
- `get_bakebook` follows common Python naming pattern (simple retrieval)

**Key Decision:** NO `TwoTierEnv` - only `BaseEnv` (3-tier)

- 3-tier is more flexible - users can use just 2 by ignoring staging
- Simpler API: one universal preset instead of two
- Most common patterns use 3 tiers (dev/staging/prod)
- **BaseEnv serves as base class for custom environments**
- **Renamed from StandardEnv because there's no universal standard for env naming**

### Env Implementation

**Approach:** Inherit from `str`, not `BaseModel`

```python
class BaseEnv(str):
    def __lt__(self, other: BaseEnv) -> bool: ...
    def __eq__(self, other) -> bool: ...
    def __hash__(self) -> int: ...
```

**Benefits:**

- Immutable by default (strings are immutable)
- No need for `frozen = True` config
- Natural string behavior (`str(env)`, comparison with strings)
- Simpler than BaseModel

**Pydantic Integration:** Via `__get_pydantic_core_schema__` (v2)

### Priority Inference

**Design:** Priority is inferred from `ENV_ORDER` list position, not stored separately.

**Comparison Rules:**

- BaseEnv: `dev < staging < prod` (index order)
- Same priority group (set): uses alphabetical as tiebreaker
- Example: `{"staging", "qa"}` → "qa" < "staging" (alphabetical tiebreaker)

---

## Implementation State (2025-01-22)

### Files Created/Modified

**`src/bakelib/environ/base.py`** (Complete)

```python
class BaseEnv(str):
    """BaseEnvironment string with comparison and Pydantic support."""

    ENV_ORDER: ClassVar[list[str | set[str]]] = ["dev", "staging", "prod"]

    def __init__(self, value: str):
        if not self._is_valid(value):
            raise ValueError(...)

    @classmethod
    def _is_valid(cls, value: str) -> bool:
        try:
            cls._get_priority_index(value)
            return True
        except ValueError:
            return False

    @classmethod
    def _flattened_env_order(cls) -> list[str]:
        """Get flattened list of all valid env names."""
        # Sorts set items alphabetically

    @classmethod
    def _get_priority_index(cls, value: str) -> int:
        """Get the priority index for a value."""

    def __lt__(self, other: str) -> bool:
        """Compare by priority (lower index = higher priority)."""
```

**`tests/unit/bakelib/environ/test_base.py`** (Complete - 43 tests)

- Test instantiation, validation, comparison, equality, hash, repr
- Test Pydantic integration
- Test inheritance
- Test edge cases (unicode, long strings, mixed ENV_ORDER)

---

## Open Questions

### 1. Bakebook Integration (Phase 3 - CRITICAL)

**Question:** How do bakebooks carry env metadata?

**Options:**

**Option A:** Add `env` field to Bakebook

```python
class Bakebook(BaseSettings):
    env: BaseEnv | None = None  # Optional
```

**Option B:** Use separate mapping

```python
env_map = {bb_prod: BaseEnv("prod"), ...}
```

**Recommendation:** Option A (add optional field to Bakebook)

### 2. Next Phase Planning

**Question:** Should we proceed with Phase 3 (Bakebook integration) or Phase 2 (presets like GcpLandingZoneEnv)?

**Current State:**

- Phase 1 (BaseEnv base class) is complete
- Phase 2 (GcpLandingZoneEnv presets) is NOT started
- The original plan had BaseEnv in `presets.py`, but we implemented it in `base.py`

**Decision Needed:** Continue with GcpLandingZoneEnv in `presets.py` or move to Bakebook integration?

---

## Technical Constraints

### Must Have

1. **Pydantic v2 compatible** - Project uses Pydantic Settings
2. **Python 3.11+** - No specific version constraints identified
3. **Backward compatible** - Existing bakefiles must continue working
4. **Type safe** - Proper type hints throughout
5. **Well tested** - Coverage > 80%, follow project test patterns

### Must NOT Have

1. **Breaking changes** - Cannot break existing bakebook behavior
2. **Complex dependencies** - Use existing project dependencies
3. **Over-engineering** - Keep simple, add features later if needed

---

## Quick Resume Instructions

To continue implementing:

1. **Read this file** - Understand design decisions and current state
2. **Decide on next phase** - GcpLandingZoneEnv presets or Bakebook integration?
3. **Read tasks.md** - Check implementation checklist
4. **Follow plan.md** - Each phase has clear acceptance criteria

**Current Phase:** Phase 1 complete, Phase 2 (BaseEnv) complete in `base.py`
**Unclear:** Should GcpLandingZoneEnv be implemented in `presets.py` or is BaseEnv sufficient?

**Next Action:** Confirm with user whether to:

- Implement GcpLandingZoneEnv in `presets.py` (as originally planned)
- Move to Phase 3 (Bakebook integration)
- Focus on other priorities

---

## Related Discussions

### User Conversation (2025-01-22)

**Key Points:**

- User confirmed `__init__` works (no need for `__new__`)
- User wants `list[str | set[str]]` type for ENV_ORDER (not `list[str] | set[str]`)
- User wants sets for equal priority: `["dev", {"staging", "qa"}, "prod"]`
- User wants priority-based comparison (not alphabetical)
- User wants test simplification with `@pytest.mark.parametrize`
- User wants NATO phonetic alphabet for test data (alpha, bravo, charlie, delta, zulu)

**Current Implementation Status:**

- BaseEnv is complete in `base.py` with all features
- 43 tests passing, full coverage of BaseEnv functionality
- Linters pass (ruff, typer)
- Ready to proceed with next phase

**Code Location:** `src/bakelib/environ/base.py` contains the complete BaseEnv implementation
