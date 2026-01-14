# Bakebook Class - Implementation Plan

**Last Updated:** 2025-01-04

---

## Executive Summary

Replace the simple `BakebookType = typer.Typer` type alias with a custom `Bakebook` class that combines Pydantic's validation capabilities with Typer's CLI functionality. This enables environment variable validation and provides a foundation for future bakebook enhancements.

**Why:** The current type alias provides no structure or validation. A proper class enables:

- Environment variable validation via Pydantic Settings
- Properties and metadata on bakebooks
- Better extensibility for future features
- Type safety and validation

**Scope:** Create `Bakebook` class, update validation logic, modify CLI integration, and ensure all tests pass. No backward compatibility needed (POC project).

---

## Current State Analysis

### Existing Architecture

```
src/bake/bakebook/type.py
├── BakebookType = typer.Typer  # Simple type alias

src/bake/bakebook/get.py
├── validate_bakebook()         # Checks isinstance(bakebook, typer.Typer)
├── get_bakebook_from_module()  # Extracts bakebook from loaded module
└── get_bakebook_from_target_dir_path()  # Main loading entry point

src/bake/cli/bake/main.py:35
├── bake_app.add_typer(bakefile_obj.bakebook)  # Integration point
```

### User API (Current)

```python
# User's bakefile.py
import typer

bakebook = typer.Typer()

@bakebook.command()
def build(prod: bool = False):
    """Build the project."""
    typer.echo(f"Building{' (prod)' if prod else ''}...")
```

### Key Constraints

1. **No backward compatibility** - This is a POC project, no production users
2. **Must pass all existing tests** - Functionality unchanged, only internal structure
3. **Two CLI architecture preserved** - `bake` (task runner) and `bakefile` (manager)

---

## Proposed Future State

### New Bakebook Class

```python
# src/bake/bakebook/bakebook.py
from pydantic import PrivateAttr
import typer
from pydantic_settings import BaseSettings


class Bakebook(BaseSettings):
    """
    Base class for bakebooks. Users inherit from this to add their own
    properties and environment variables.

    Example:
        class MyBakebook(Bakebook):
            database_url: str
            debug: bool = False

            def get_config(self):
                return self.database_url
    """
    # Internal Typer app (PrivateAttr: no validation, auto-excluded)
    _app: typer.Typer = PrivateAttr(default_factory=typer.Typer)

    # Optional metadata
    name: str = ""
    description: str = ""

    # ========== Public API for Users ==========

    def command(self, *args, **kwargs):
        """Register a command on the bakebook."""
        return self._app.command(*args, **kwargs)
```

### User API (Future)

**Minimal:**

```python
from bake import Bakebook

class MyBakebook(Bakebook):
    pass

bakebook = MyBakebook()

@bakebook.command()
def build(prod: bool = False):
    """Build the project."""
    typer.echo(f"Building{' (prod)' if prod else ''}...")
```

**With Environment Variables (Direct on Class):**

```python
from bake import Bakebook


class MyBakebook(Bakebook):
    # Env vars loaded automatically by BaseSettings
    database_url: str
    debug: bool = False
    project_name: str = "myproject"

    def get_config(self):
        return f"{self.database_url}/{self.project_name}"


bakebook = MyBakebook()  # Loads from env: DATABASE_URL, DEBUG

@bakebook.command()
def migrate():
    """Run database migrations."""
    url = bakebook.database_url  # Access directly
    typer.echo(f"Migrating to {url}...")
```

**With Custom Methods:**

```python
class MyBakebook(Bakebook):
    api_key: str
    region: str = "us-east-1"

    def get_client(self):
        return Client(self.api_key, self.region)

bakebook = MyBakebook()

@bakebook.command()
def deploy():
    client = bakebook.get_client()
    client.deploy()
```

---

## Implementation Phases

### Phase 1: Create Bakebook Class Foundation

**Effort:** M (Medium)

**Tasks:**

1. Create `src/bake/bakebook/bakebook.py`
2. Implement `Bakebook(BaseSettings)` class
3. Add internal `_app` field with `PrivateAttr(default_factory=typer.Typer)`
4. Add metadata fields (`name`, `description`)
5. Implement `command()` delegation method

**Acceptance Criteria:**

- Class can be inherited: `class MyBakebook(Bakebook): pass`
- Class can be instantiated: `bakebook = MyBakebook()`
- Commands can be registered: `@bakebook.command()` works
- `_app` accessible via `bakebook._app` (for framework)
- `_app` excluded from `model_dump()` (PrivateAttr)

---

### Phase 2: Unit Tests for Bakebook Class

**Effort:** M (Medium)

**Tasks:**

1. Create `tests/bake/bakebook/test_bakebook.py`
2. Test: Inherit from Bakebook
3. Test: Create empty subclass
4. Test: Add fields to subclass
5. Test: Add methods to subclass
6. Test: Command registration via `@bakebook.command()`
7. Test: `_app` accessible and is typer.Typer instance
8. Test: `_app` excluded from serialization (PrivateAttr)
9. Test: BaseSettings env var loading works

**Acceptance Criteria:**

- All unit tests pass
- Coverage for public methods
- Error cases tested

---

### Phase 3: Update Validation Logic

**Effort:** S (Small)

**Tasks:**

1. Update `validate_bakebook()` in `src/bake/bakebook/get.py`
2. Change isinstance check from `typer.Typer` to `Bakebook`
3. Update error messages to reference `Bakebook` instead of `BakebookType`
4. Update type hints in `get_bakebook_from_module()` return type
5. Update type hints in `get_bakebook_from_target_dir_path()` return type

**Acceptance Criteria:**

- `validate_bakebook()` accepts `Bakebook` instances
- `validate_bakebook()` rejects non-`Bakebook` instances
- Type hints use `Bakebook` instead of `BakebookType`

---

### Phase 4: Update CLI Integration

**Effort:** S (Small)

**Tasks:**

1. Update `src/bake/cli/bake/main.py` line 35
2. Change `bake_app.add_typer(bakebook)` to `bake_app.add_typer(bakebook._app)`
3. Update type hints in `src/bake/cli/common/obj.py`
4. Change `bakebook: BakebookType | None` to `bakebook: Bakebook | None`

**Acceptance Criteria:**

- `bake` CLI loads and runs `Bakebook` instances
- Commands execute correctly
- Context propagation works

---

### Phase 5: Update Bakebook Type Alias

**Effort:** S (Small)

**Decision Point:** What to do with `src/bake/bakebook/type.py`?

**Option A:** Delete entirely

- Remove `type.py` file
- Update all imports from `bake.bakebook.type` to `bake.bakebook.bakebook`

**Option B:** Re-export for convenience

- Change to: `from .bakebook import Bakebook; __all__ = ["Bakebook"]`
- Existing imports continue to work

**Tasks:**

1. Decide on Option A or B
2. If Option A: Delete `type.py`, update imports
3. If Option B: Update `type.py` to re-export `Bakebook`
4. Update `src/bake/bakebook/__init__.py` if needed

**Acceptance Criteria:**

- No import errors
- Type hints resolve correctly

---

### Phase 6: Export Bakebook from Root Package

**Effort:** XS (Extra Small)

**Tasks:**

1. Update `src/bake/__init__.py`
2. Add `Bakebook` to `__all__`
3. Import `Bakebook` from `bake.bakebook.bakebook`

**Acceptance Criteria:**

- `from bake import Bakebook` works
- User-facing convenience import

---

### Phase 7: Update Examples and Samples

**Effort:** S (Small)

**Files to Update:**

1. `examples/simple/bakefile.py`
2. `src/bake/samples/simple.py`
3. Any other example bakefiles

**Tasks:**

1. Replace `import typer` with `from bake import Bakebook`
2. Replace `bakebook = typer.Typer()` with `bakebook = Bakebook()`
3. Verify `@bakebook.command()` still works
4. Test example bakefiles manually

**Acceptance Criteria:**

- All example bakefiles use `Bakebook`
- `bake` CLI runs examples successfully
- Help text displays correctly

---

### Phase 8: Update Existing Tests

**Effort:** M (Medium)

**Files to Update:**

1. `tests/bake/bakebook/test_get.py`
2. `tests/bake/cli/common/test_obj.py`
3. `tests/bake/cli/bake/test_bake_main.py`
4. Any other test files using `typer.Typer()` for bakebooks

**Tasks:**

1. Search for all `typer.Typer()` usages in tests
2. Replace bakebook instances with `Bakebook()`
3. Update `isinstance` checks
4. Update type hints in test assertions
5. Verify all tests pass

**Acceptance Criteria:**

- All existing tests pass
- No test uses `typer.Typer()` for bakebook creation
- Test coverage maintained

---

### Phase 9: Full Test Suite Validation

**Effort:** S (Small)

**Tasks:**

1. Run `make test` to execute full test suite
2. Run `make lint` to check code quality
3. Fix any failing tests
4. Fix any linting issues
5. Run `bake` CLI against examples
6. Test with custom bakefiles

**Acceptance Criteria:**

- All tests pass
- Linting passes
- `bake` CLI works with new `Bakebook` class
- No regressions

---

### Phase 10: Documentation Updates

**Effort:** M (Medium)

**Files to Update:**

1. `.claude/BEST_PRACTICES.md`
2. `.claude/PROJECT_KNOWLEDGE.md` (if exists)
3. `.claude/TROUBLESHOOTING.md` (if exists)
4. Any README files
5. Code comments mentioning `BakebookType`

**Tasks:**

1. Update BEST_PRACTICES.md bakebook examples
2. Update architecture documentation
3. Update troubleshooting guides
4. Remove references to `BakebookType` alias
5. Add examples of env validation
6. Document new `Bakebook` class API

**Acceptance Criteria:**

- Documentation reflects new `Bakebook` class
- Examples use `from bake import Bakebook`
- Env validation examples provided
- No outdated `BakebookType` references

---

## Risk Assessment

### High Risks

| Risk                          | Impact | Probability | Mitigation                                     |
| ----------------------------- | ------ | ----------- | ---------------------------------------------- |
| Typer integration breaks      | High   | Medium      | Comprehensive testing of CLI integration early |
| Pydantic serialization issues | Medium | Low         | Use `exclude=True` for `_app` and `env`        |

### Medium Risks

| Risk                                                   | Impact | Probability | Mitigation                     |
| ------------------------------------------------------ | ------ | ----------- | ------------------------------ |
| Test suite has many hardcoded `typer.Typer` references | Medium | High        | Systematic grep and replace    |
| Examples break after update                            | Low    | Medium      | Manual testing of all examples |

### Low Risks

| Risk                               | Impact | Probability | Mitigation                       |
| ---------------------------------- | ------ | ----------- | -------------------------------- |
| User confusion about env parameter | Low    | Low         | Clear documentation and examples |
| Performance regression             | Low    | Low         | Pydantic validation is fast      |

---

## Success Metrics

### Functional Requirements

- [ ] `Bakebook` class created and working
- [ ] All existing tests pass
- [ ] `bake` CLI runs with new `Bakebook` instances
- [ ] `bakefile` CLI continues to work
- [ ] Env validation works via `BaseSettings`
- [ ] Examples updated and working

### Quality Requirements

- [ ] Code follows BEST_PRACTICES.md
- [ ] No docstrings added (per policy)
- [ ] Linting passes (`make lint`)
- [ ] Test coverage maintained

### Developer Experience

- [ ] Clean import: `from bake import Bakebook`
- [ ] Clear error messages
- [ ] Minimal breaking changes (internal only)

---

## Required Resources and Dependencies

### External Dependencies

- `pydantic` - Already in project
- `pydantic-settings` - **Need to verify if installed**
- `typer` - Already in project

### Internal Dependencies

- `src/bake/bakebook/get.py` - Needs update
- `src/bake/cli/bake/main.py` - Needs update
- `src/bake/cli/common/obj.py` - Needs update
- `src/bake/__init__.py` - Needs export

### Tools

- `make test` - Test runner
- `make lint` - Linter
- pytest - Test framework

---

## Timeline Estimates

| Phase                           | Estimated Effort | Dependencies     |
| ------------------------------- | ---------------- | ---------------- |
| Phase 1: Create Bakebook Class  | M                | None             |
| Phase 2: Unit Tests             | M                | Phase 1          |
| Phase 3: Update Validation      | S                | Phase 1          |
| Phase 4: Update CLI Integration | S                | Phase 1, Phase 3 |
| Phase 5: Type Alias Decision    | S                | Phase 4          |
| Phase 6: Export from Root       | XS               | Phase 1          |
| Phase 7: Update Examples        | S                | Phase 6          |
| Phase 8: Update Tests           | M                | Phase 1          |
| Phase 9: Full Validation        | S                | All phases       |
| Phase 10: Documentation         | M                | All phases       |

**Total Estimated Effort:** ~8-10 hours

**Critical Path:** Phase 1 → Phase 3 → Phase 4 → Phase 9

---

## Open Questions

### Decided

1. **Inheritance base** → `Bakebook(BaseSettings)` - Users inherit to add env vars
2. **User API** → `class MyBakebook(Bakebook): ...` then `bakebook = MyBakebook()`
3. **Private field** → `PrivateAttr` for `_app` (no validation needed, auto-excluded)
4. **Migration period** → No backward compatibility (break change OK)
5. **Type alias fate** → To be decided (Option A: delete, Option B: re-export)
6. **Env pattern** → Users define env vars directly on subclass (no separate `env` field)
7. **Import from root** → Yes, `from bake import Bakebook`

### Pending

1. **`BakebookType` file** → Delete or re-export? (Phase 5 decision point)

---

## Implementation Notes

### Pydantic Configuration

**Simplified:** No `model_config` needed! `PrivateAttr` bypasses all validation.

```python
from pydantic_settings import BaseSettings
from pydantic import PrivateAttr
import typer


class Bakebook(BaseSettings):  # ← Inherits from BaseSettings for env loading
    _app: typer.Typer = PrivateAttr(default_factory=typer.Typer)
    # No arbitrary_types_allowed needed!
```

### Field Definition

```python
# PrivateAttr: No validation, auto-excluded from serialization
_app: typer.Typer = PrivateAttr(default_factory=typer.Typer)
```

**Why PrivateAttr?**

- No type validation needed (bypasses arbitrary_types_allowed requirement)
- Auto-excluded from `model_dump()`
- Private by convention (underscore prefix)

### User-Defined Fields (Inheritance Pattern)

Users define env vars directly on their subclass:

```python
class MyBakebook(Bakebook):
    # These load from env vars automatically (BaseSettings)
    database_url: str
    debug: bool = False
    api_key: str

    # Custom methods
    def get_client(self):
        return Client(self.api_key)

# Usage
bakebook = MyBakebook()  # Loads DATABASE_URL, DEBUG, API_KEY from env
url = bakebook.database_url  # Direct access
```

### Key Methods to Delegate

From `typer.Typer`:

- `command()` - Register commands (public API for users)

### Validation Function Update

```python
# Before
def validate_bakebook(bakebook: Any, bakebook_name: str) -> BakebookType:
    if not isinstance(bakebook, BakebookType):
        raise BakebookError(...)

# After
def validate_bakebook(bakebook: Any, bakebook_name: str) -> Bakebook:
    if not isinstance(bakebook, Bakebook):
        raise BakebookError(...)
```

### CLI Integration Point

```python
# main.py line 35
# Before
bake_app.add_typer(bakefile_obj.bakebook)

# After
bake_app.add_typer(bakefile_obj.bakebook._app)
```

---

## Next Steps

1. **Implement Phase 1** - Create `Bakebook` class foundation
2. **Implement Phase 2** - Write comprehensive unit tests
3. **Verify Phases 3-4** - Update validation and CLI integration
4. **Decide Phase 5** - Choose Type Alias approach (delete or re-export)
5. **Complete Phases 6-10** - Export, update examples/tests, validate, document
6. **Run full test suite** - Ensure no regressions
7. **Manual testing** - Test `bake` CLI with various bakefiles

---

## References

### Key Files

- `src/bake/bakebook/type.py` - Current type alias (to be replaced/updated)
- `src/bake/bakebook/get.py` - Bakebook loading and validation
- `src/bake/cli/bake/main.py` - CLI integration point
- `src/bake/cli/common/obj.py` - BakefileObject with bakebook field
- `examples/simple/bakefile.py` - User example

### Related Documentation

- `.claude/BEST_PRACTICES.md` - Coding standards (especially bakebook patterns)
- `.claude/PROJECT_KNOWLEDGE.md` - Architecture overview
- `.dev/README.md` - Dev docs pattern

### External References

- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Typer Documentation](https://typer.tiangolo.com/)
