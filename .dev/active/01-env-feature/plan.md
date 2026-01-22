# Env Feature - Implementation Plan

**Last Updated: 2025-01-22**

---

## Executive Summary

Implement an **Env (Environment)** feature for bakefile that allows users to define environment-aware bakebooks with automatic selection based on environment variables. This feature enables configuration management across multiple environments (dev, staging, prod, etc.) with a clean, programmatic API.

**Key Benefits:**

- Environment-aware bakebook selection
- Type-safe environment configuration
- Extensible base class for custom environments
- Common presets (BaseEnv, GcpLandingZoneEnv) for typical use cases

---

## Current State Analysis

### Existing Codebase

**Bakebook Architecture:**

- `Bakebook` class extends Pydantic `BaseSettings`
- Supports env var loading from `.env` files
- Commands registered via `@command()` decorator
- Bakelib provides reusable extensions (BaseSpace, PythonSpace)

**Existing Utils:**

- `src/bake/utils/env.py` - Contains only NO_COLOR detection (unrelated to this feature)

**Test Structure:**

- Unit tests: `tests/unit/bakelib/` (fast, mocked)
- Integration tests: `tests/integration/` (slow, real subprocess)
- Tests mirror source structure

**Reference Implementation:**

- User has `EnvironmentCode` class in another project with similar comparison logic
- Uses `str` inheritance for clean string behavior
- Pydantic integration via `__get_pydantic_core_schema__`

### Gap Analysis

**Missing:**

1. No environment abstraction for bakebook selection
2. No way to attach env metadata to bakebooks
3. No selector/get_bakebook function for env-based selection
4. No common environment presets

**User Use Case:**

```python
# In user's bakefile.py
bb_prod = Bakebook(..., env=BaseEnv("prod"))
bb_staging = Bakebook(..., env=BaseEnv("staging"))
bb_dev = Bakebook(..., env=BaseEnv("dev"))

# Select based on BAKE_ENV env var
bakebook = get_bakebook([bb_prod, bb_staging, bb_dev])
```

---

## Proposed Future State

### Architecture

```
src/bakelib/environ/
├── __init__.py       # Public API exports
├── base.py           # Env base class
├── presets.py        # BaseEnv, GcpLandingZoneEnv
└── selector.py       # get_bakebook() function
```

### API Design

**1. Env Base Class (`base.py`)**

```python
class Env(str):
    """Environment string with comparison and Pydantic support."""

    # Comparison: lower value = higher priority (default fallback)
    def __lt__(self, other: Env) -> bool: ...
    def __eq__(self, other) -> bool: ...
    def __hash__(self) -> int: ...

    # Pydantic integration
    @classmethod
    def __get_pydantic_core_schema__(cls, ...): ...
    @classmethod
    def validate(cls, v): ...
```

**2. Presets (`presets.py`)**

```python
class BaseEnv(Env):
    """Base environment class with ENV_ORDER pattern.

    Default: dev, staging, prod (common but customizable).
    There is no universal standard for env naming, so users are
    expected to inherit and customize ENV_ORDER for their needs.

    Can be used directly with defaults or inherited for custom envs.
    """
    ENV_ORDER = ["dev", "staging", "prod"]

    def __init__(self, value: str):
        valid_envs = self._flatten_env_order(self.ENV_ORDER)
        if value not in valid_envs:
            raise ValueError(f"Invalid env: {value}. Valid: {valid_envs}")
        super().__init__(value)

    @classmethod
    def _flatten_env_order(cls, env_order):
        """Handle nested lists for equal priority tiers.

        Example: ["d", "n", ["p", "s", "b"]] -> ["d", "n", "p", "s", "b"]
        """
        flat = []
        for item in env_order:
            if isinstance(item, list):
                flat.extend(item)
            else:
                flat.append(item)
        return flat

    def __lt__(self, other: str) -> bool:
        """Compare by priority (lower index = higher priority)."""
        if type(other) is not type(self):
            return NotImplemented
        self_priority = self._get_priority_index(str(self))
        other_priority = self._get_priority_index(str(other))
        return self_priority < other_priority

    @classmethod
    def _get_priority_index(cls, env: str) -> int:
        """Get priority index for comparison.

        Items in same nested list have SAME priority index.
        """
        for idx, item in enumerate(cls.ENV_ORDER):
            if isinstance(item, list):
                if env in item:
                    return idx
            else:
                if item == env:
                    return idx
        raise ValueError(f"Env {env} not found in ENV_ORDER")

class GcpLandingZoneEnv(BaseEnv):
    """GCP Landing Zone base environments.

    Tiers: d (dev) < n (nonprod) < p/s/b/c/net (shared)

    Inherits from BaseEnv to demonstrate extensibility pattern.
    Users can create custom envs by inheriting and updating ENV_ORDER.
    """
    ENV_ORDER = ["d", "n", ["p", "s", "b", "c", "net"]]
    # Inherits __init__ validation from BaseEnv!

class GcpLandingZoneInstanceEnv(GcpLandingZoneEnv):
    """GCP Landing Zone with instance support (d1, d2, n1, n2, etc.).

    Base environments: d, n, p, s, b, c, net
    Instances: d1, d2, ... (dev tier), n1, n2, ... (nonprod tier)

    Priority within tier: d3 < d2 < d1 < d (higher number = lower priority)
    """
    # Inherits ENV_ORDER from GcpLandingZoneEnv
    # Adds instance validation and priority inference
```

**Key Design Pattern:**

- **`ENV_ORDER` list pattern** - Easy customization by inheritance
- **Nested lists for equal priority** - `["a", ["b", "c"]]` means b == c
- **Validation in `__init__` only** - No `from_name` method needed
- **Priority inference** - Lower index = higher priority
- **No hardcoded class attributes** (e.g., `DEV = Env("dev")`)
- **BaseEnv as base class** - Designed for inheritance with sensible defaults

**3. Selector (`selector.py`)**

```python
def get_bakebook(
    bakebooks: list[Bakebook],
    *,
    env_var: str = "BAKE_ENV",
    fallback_on_no_match: bool = True,
) -> Bakebook:
    """
    Select bakebook based on environment variable.

    Reads env_var (default: BAKE_ENV), matches against bakebook.env,
    returns matching bakebook or lowest priority (default).
    """
```

### Bakebook Integration

**Option: Add `env` parameter to Bakebook**

```python
# Existing Bakebook class may need:
class Bakebook(BaseSettings):
    env: Env | None = None  # Optional env metadata
```

**Or: Use composition/wrapper pattern**

```python
# User stores bakebook with env
bb_prod = Bakebook(...)
# Later selected by get_bakebook using env matching
```

---

## Implementation Phases

### Phase 1: Core Infrastructure

**Effort: M (2-3 hours)**

**Goal:** Create base Env class with comparison and Pydantic support.

**Tasks:**

1. Create `src/bakelib/env/` directory structure
2. Implement `Env` base class in `base.py`
3. Add comparison operators (`__lt__`, `__eq__`, `__hash__`)
4. Add Pydantic v2 integration
5. Create `__init__.py` with exports

**Acceptance Criteria:**

- `Env` can be instantiated and compared
- `Env("dev") < Env("prod")` works
- Pydantic models can use `Env` as field type
- String comparison works: `Env("dev") == "dev"`

---

### Phase 2: Environment Presets

**Effort: M (2-3 hours)**

**Goal:** Implement BaseEnv (base class) and GcpLandingZoneEnv (demonstrates inheritance pattern).

**Tasks:**

1. Implement `BaseEnv` in `presets.py`
    - `ENV_ORDER = ["dev", "staging", "prod"]`
    - Validation in `__init__` with `_flatten_env_order` helper
    - Handle nested lists for equal priority tiers
    - Implement `_get_priority_index` for comparison
    - No hardcoded class attributes
    - Priority: dev < staging < prod (index order)

2. Implement `GcpLandingZoneEnv(BaseEnv)` in `presets.py`
    - Inherits from BaseEnv
    - `ENV_ORDER = ["d", "n", ["p", "s", "b", "c", "net"]]` (nested list)
    - Tiers: d (dev) < n (nonprod) < p/s/b/c/net (shared)
    - Inherits validation from BaseEnv
    - Demonstrates extensibility pattern

3. Implement `GcpLandingZoneInstanceEnv(GcpLandingZoneEnv)` in `presets.py`
    - Inherits from GcpLandingZoneEnv
    - Adds instance support: d1, d2, n1, n2, etc.
    - Priority within tier: d3 < d2 < d1 < d
    - Override `__init__` to validate and normalize instances

4. Document priority inference rules
5. Update `__init__.py` exports

**Acceptance Criteria:**

- `BaseEnv("dev") < BaseEnv("staging") < BaseEnv("prod")`
- `BaseEnv("staging")` creates valid env
- `BaseEnv("invalid")` raises ValueError
- `GcpLandingZoneEnv("d") < GcpLandingZoneEnv("n") < GcpLandingZoneEnv("p")`
- `GcpLandingZoneEnv("p") == GcpLandingZoneEnv("s") == GcpLandingZoneEnv("b")` (shared tier)
- `GcpLandingZoneEnv("d1")` raises ValueError (no instances in base class)
- `GcpLandingZoneInstanceEnv("d")` and `GcpLandingZoneInstanceEnv("d1")` both valid
- `GcpLandingZoneInstanceEnv("d3") < GcpLandingZoneInstanceEnv("d2") < GcpLandingZoneInstanceEnv("d1") < GcpLandingZoneInstanceEnv("d")`

---

### Phase 3: Bakebook Integration

**Effort: S (1-2 hours)**

**Goal:** Enable bakebooks to carry env metadata.

**Tasks:**

1. Decide on integration approach
    - Option A: Add `env` field to Bakebook
    - Option B: Use wrapper/composition
    - Document decision in context.md

2. Implement chosen approach
3. Update Bakebook class if needed
4. Ensure backward compatibility (env is optional)

**Acceptance Criteria:**

- Bakebooks can be created with env metadata
- Existing bakebooks without env still work
- Env is accessible on bakebook instance

---

### Phase 4: Selector Function

**Effort: M (2-3 hours)**

**Goal:** Implement `get_bakebook()` for env-based selection.

**Tasks:**

1. Implement `get_bakebook()` in `selector.py`
2. Read environment variable (default: `BAKE_ENV`)
3. Match env value to bakebook's env
4. Fall back to lowest priority (min) if no match
5. Add `fallback_on_no_match` parameter
6. Handle edge cases:
    - Empty bakebook list
    - All bakebooks without env
    - Env var set but no match

**Acceptance Criteria:**

- `get_bakebook([bb_dev, bb_prod])` returns based on `BAKE_ENV`
- Falls back to `dev` when `BAKE_ENV` unset
- Configurable env_var name
- Configurable fallback behavior

---

### Phase 5: Testing

**Effort: L (4-6 hours)**

**Goal:** Comprehensive test coverage for all components.

**Tasks:**

1. Create `tests/unit/bakelib/env/` directory
2. Unit tests for `Env` base class
    - Comparison operators
    - String equality
    - Hash behavior
    - Pydantic validation

3. Unit tests for `BaseEnv`
    - Priority ordering
    - Validation against ENV_ORDER
    - Invalid env raises ValueError
    - Nested list flattening

4. Unit tests for `GcpLandingZoneEnv`
    - Inherits from BaseEnv
    - Priority ordering (d < n < p)
    - Shared tier equality (p == s == b == c == net)
    - Rejects instances (d1, n1 should raise ValueError)

5. Unit tests for `GcpLandingZoneInstanceEnv`
    - Inherits from GcpLandingZoneEnv
    - Accepts base envs (d, n, p, s, b, c, net)
    - Accepts instances (d1, d2, n1, n2, etc.)
    - Priority within tier (d3 < d2 < d1 < d)

6. Unit tests for `get_bakebook()`
    - Env var matching
    - Fallback behavior
    - Edge cases
    - Mocked env var reads

7. Integration tests
    - Real .env file
    - Real bakebook instances
    - End-to-end selection

**Acceptance Criteria:**

- All tests pass (`make test`)
- Coverage > 80% for new code
- No regression in existing tests

---

### Phase 6: Documentation & Examples

**Effort: S (1-2 hours)**

**Goal:** Clear documentation and usage examples.

**Tasks:**

1. Create example bakefile using env feature
2. Add usage example in examples/
3. Update CLAUDE.md if needed
4. Document API in code (docstrings added by developer later)

**Acceptance Criteria:**

- Example demonstrates BaseEnv usage
- Example demonstrates GcpLandingZoneEnv usage
- Example demonstrates GcpLandingZoneInstanceEnv usage
- Example demonstrates get_bakebook()
- Example shows custom env inheriting from BaseEnv
- Can run example successfully

---

## Risk Assessment

### High Risk Items

| Risk                                      | Impact | Probability | Mitigation                                       |
| ----------------------------------------- | ------ | ----------- | ------------------------------------------------ |
| Bakebook integration breaks existing code | High   | Low         | Keep env optional, ensure backward compatibility |
| Pydantic v2 compatibility issues          | Medium | Low         | Follow existing patterns, test thoroughly        |
| Priority inference logic complexity       | Medium | Medium      | Keep simple, document rules, extensive tests     |

### Medium Risk Items

| Risk                                         | Impact | Probability | Mitigation                           |
| -------------------------------------------- | ------ | ----------- | ------------------------------------ |
| Selector edge cases (empty list, no match)   | Medium | Low         | Add validation, clear error messages |
| Performance (env var reads)                  | Low    | Low         | Cache reads, use os.getenv           |
| Naming conflicts (BaseEnv/GcpLandingZoneEnv) | Low    | Low         | Names are descriptive enough         |

---

## Success Metrics

1. **Functional:**
    - Users can define env-aware bakebooks
    - `get_bakebook()` correctly selects based on env var
    - All comparison operators work correctly
    - Pydantic integration works

2. **Quality:**
    - All tests pass (`make test`)
    - No linting errors (`make lint`)
    - Coverage > 80% for new code

3. **Usability:**
    - Clear API (`from bake.environ import Env, BaseEnv, get_bakebook`)
    - Simple examples work
    - Backward compatible with existing bakebooks
    - Easy to customize by inheritance (ENV_ORDER pattern)

---

## Required Resources and Dependencies

### Dependencies

- **Pydantic v2** (already in project)
- **Python 3.11+** (for StrEnum if used, but we're using `str` inheritance)

### External References

- User's `EnvironmentCode` class: `/Users/wisl/Desktop/vault/abcs-repo/data-kit/abcs_dk/glz/environment_code.py`
- Pydantic v2 docs for custom types

### Internal Files

- `src/bake/bakebook/bakebook.py` - Bakebook class
- `src/bakelib/space/base.py` - BaseSpace pattern reference
- `tests/unit/bakelib/` - Test pattern reference

---

## Timeline Estimates

| Phase                         | Effort   | Duration        |
| ----------------------------- | -------- | --------------- |
| Phase 1: Core Infrastructure  | M        | 2-3 hours       |
| Phase 2: Environment Presets  | M        | 2-3 hours       |
| Phase 3: Bakebook Integration | S        | 1-2 hours       |
| Phase 4: Selector Function    | M        | 2-3 hours       |
| Phase 5: Testing              | L        | 4-6 hours       |
| Phase 6: Documentation        | S        | 1-2 hours       |
| **Total**                     | **L/XL** | **12-19 hours** |

---

## Open Questions

1. **Bakebook Integration Approach:**
    - Should Bakebook have an `env` field?
    - Or should we use a separate mapping/dict?
    - **Decision needed in Phase 3**

2. **LandingZoneEnv Shortcut Support:**
    - Should `d1`, `n1` be auto-parsed or explicit?
    - User's reference uses regex parsing
    - **Decision needed in Phase 2**

3. **Selector Error Handling:**
    - Should `get_bakebook()` raise or return None on error?
    - Current plan: return min() on no match (configurable)
    - **Confirm before Phase 4**

4. **Env Var Name:**
    - Fixed as `BAKE_ENV`?
    - Configurable per selector call?
    - **Decision: Configurable via parameter, default `BAKE_ENV`**

---

## RESOLVED Decisions (2025-01-22)

### Naming: BaseEnv vs StandardEnv

**Decision:** Use `BaseEnv` instead of `StandardEnv`

**Rationale:**

- There is NO universal standard for environment naming
- Different orgs use: dev/staging/prod, dev/prod, d/n/p, etc.
- "BaseEnv" is honest - it's a base class with common defaults
- Users expected to inherit and customize `ENV_ORDER`
- "Standard" implies dev/staging/prod is universal (misleading)

**Design Pattern:**

```python
class BaseEnv(Env):
    """Base environment class with ENV_ORDER pattern.

    Default: dev, staging, prod (common but customizable).
    There is no universal standard for env naming.
    """
    ENV_ORDER = ["dev", "staging", "prod"]

    def __init__(self, value: str):
        valid_envs = self._flatten_env_order(self.ENV_ORDER)
        if value not in valid_envs:
            raise ValueError(f"Invalid env: {value}. Valid: {valid_envs}")
        super().__init__(value)

    @classmethod
    def _flatten_env_order(cls, env_order):
        """Handle nested lists for equal priority tiers."""
        flat = []
        for item in env_order:
            if isinstance(item, list):
                flat.extend(item)
            else:
                flat.append(item)
        return flat
```

**Benefits:**

- No hardcoded class attributes (DEV, STAGING, PROD)
- Easy to customize by inheritance
- Users can create Custom4Tier by inheriting and updating `ENV_ORDER`
- Validation happens in `__init__` only
- **Designed as base class for custom environments**
- **Honest about lack of universal standard**

### GcpLandingZoneEnv Design

**Decision:** GCP Landing Zone preset inherits from BaseEnv

**Naming:** `GcpLandingZoneEnv` (specific to GCP Landing Zone)

**Inheritance:** `class GcpLandingZoneEnv(BaseEnv)`

**Rationale:**

- Demonstrates BaseEnv extensibility pattern
- Users see: "Oh, I just inherit from BaseEnv and change ENV_ORDER"
- Proves the pattern works for different use cases
- DRY - no duplication of validation logic

**Design:**

```python
class GcpLandingZoneEnv(BaseEnv):
    """GCP Landing Zone base environments."""
    ENV_ORDER = ["d", "n", ["p", "s", "b", "c", "net"]]
    # Inherits __init__ validation from BaseEnv!
```

**Tiers:** d (dev) < n (nonprod) < p/s/b/c/net (shared)
**Shared:** p = s = b = c = net (equal priority, using nested list)

### GcpLandingZoneInstanceEnv Design

**Decision:** Separate class for instance support (d1, d2, n1, n2, etc.)

**Inheritance:** `class GcpLandingZoneInstanceEnv(GcpLandingZoneEnv)`

**Rationale:**

- Clear separation: "base environment" vs "environment instance"
- d1, d2 are not part of GCP Landing Zone documentation convention
- Users choose which level of complexity they need
- Simpler base class (GcpLandingZoneEnv) stays close to documentation

**Design:**

```python
class GcpLandingZoneInstanceEnv(GcpLandingZoneEnv):
    """GCP Landing Zone with instance support."""
    # Inherits ENV_ORDER from parent
    # Adds instance validation and priority inference
```

**Accepts:** d, n, p, s, b, c, net (base) AND d1, d2, n1, n2 (instances)

**Priority within tier:** d3 < d2 < d1 < d (higher number = lower priority)

### Nested List for Equal Priority

**Decision:** Use nested list notation `["d", "n", ["p", "s", "b"]]`

**Meaning:** Items in nested list have equal priority

**Implementation:** `BaseEnv._flatten_env_order()` handles both flat and nested lists

**Benefits:**

- Clear visual notation for equal priority tiers
- Flexible for custom environments
- Single source of truth (ENV_ORDER)

---

## Future Enhancements (Out of Scope)

1. Additional preset environments (AWS-style, Azure-style)
2. Env validation with custom rules
3. Env hierarchies (inheritance between envs)
4. Env-specific command overrides
5. Visual env status in CLI output
