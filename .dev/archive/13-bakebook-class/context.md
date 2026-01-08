# Bakebook Class - Context

**Last Updated:** 2025-01-04

---

## SESSION PROGRESS (2025-01-04)

### ✅ COMPLETED

- Initial planning and design discussion complete
- Dev docs structure created (plan.md, context.md, tasks.md)
- All design decisions finalized

### 🟡 IN PROGRESS

- None yet (planning phase complete, awaiting implementation go-ahead)

### ⚠️ BLOCKERS

- None

---

## Design Decisions Made

### 1. Architecture: Inheritance from BaseSettings

**Decision:** Use `class Bakebook(BaseSettings)` with `PrivateAttr` for `_app`

**Why:**

- `BaseSettings` provides automatic env var loading for user-defined fields
- `PrivateAttr` bypasses Pydantic validation (no `arbitrary_types_allowed` needed)
- Auto-excluded from serialization
- Users inherit and add their own env vars directly

**Implementation:**

```python
from pydantic_settings import BaseSettings
from pydantic import PrivateAttr
import typer


class Bakebook(BaseSettings):
    _app: typer.Typer = PrivateAttr(default_factory=typer.Typer)
    # No arbitrary_types_allowed needed!

    def command(self, *args, **kwargs):
        return self._app.command(*args, **kwargs)
```

**User API:**

```python
class MyBakebook(Bakebook):
    # Env vars loaded automatically
    database_url: str
    debug: bool = False

    def get_config(self):
        return self.database_url

bakebook = MyBakebook()  # Loads from env
url = bakebook.database_url  # Direct access
```

---

### 2. PrivateAttr vs Field(exclude=True)

**Discovery:** `PrivateAttr` bypasses all validation and auto-excludes from serialization.

**POC Results:**

```python
# Test 1: WITHOUT arbitrary_types_allowed, WITH PrivateAttr
# Result: ✓ Success! (PrivateAttr doesn't validate)

# Test 2b: Does PrivateAttr validate type?
# Result: ✗ NO VALIDATION: PrivateAttr accepts wrong type!
```

**Conclusion:** Use `PrivateAttr` - simpler, no `arbitrary_types_allowed` needed.

---

### 3. User API: Inheritance Pattern

**Decision:** Users inherit from `Bakebook` to add their own fields and methods

**Why:** Enables OOP-style bakebooks with custom properties and helper methods

**Example:**

```python
class MyBakebook(Bakebook):
    project_name: str = "myproject"
    api_key: str

    def get_client(self):
        return Client(self.api_key, self.project_name)

bakebook = MyBakebook()

@bakebook.command()
def deploy():
    client = bakebook.get_client()
    client.deploy()
```

---

### 4. No Separate Env Field

**Decision:** Users define env vars directly on their subclass (no `env: BaseSettings` field)

**Why:** Cleaner API - direct access (`bakebook.database_url` vs `bakebook.env.database_url`)

---

### 5. No Backward Compatibility

**Decision:** Breaking change is acceptable

**Why:** This is a POC project with no production users yet.

**Implications:**

- Change `validate_bakebook()` to check `isinstance(bakebook, Bakebook)`
- Reject old `typer.Typer()` instances
- Update all examples and tests

---

### 6. Root Package Export

**Decision:** Export `Bakebook` from `bake` root package

**Implementation:**

```python
# src/bake/__init__.py
from bake.bakebook.bakebook import Bakebook

__all__ = ["Context", "__version__", "Bakebook"]
```

**User experience:**

```python
from bake import Bakebook  # Clean and simple
```

---

### 7. BakebookType Alias: TBD

**Status:** Decision pending for Phase 5

**Options:**

- **Option A:** Delete `src/bake/bakebook/type.py` entirely
- **Option B:** Keep as re-export: `from .bakebook import Bakebook`

**Factors to consider:**

- Any external code importing from `bake.bakebook.type`?
- Migration path for any existing references

---

## Key Files and Purposes

### Core Implementation Files

**`src/bake/bakebook/bakebook.py`** (TO BE CREATED)

- Main `Bakebook` class implementation
- Composes `BaseModel` with internal `typer.Typer`
- Delegates `command()` and `callback()` methods
- Provides `to_typer()` for framework integration

**`src/bake/bakebook/type.py`** (EXISTING, TO BE DECIDED)

- Current: `BakebookType = typer.Typer`
- Future: Delete or convert to re-export

**`src/bake/bakebook/get.py`** (NEEDS UPDATE)

- `validate_bakebook()` - Line 78-89: Change isinstance check to `Bakebook`
- `get_bakebook_from_module()` - Line 92-100: Update return type hint
- `get_bakebook_from_target_dir_path()` - Line 103-112: Update return type hint

**`src/bake/bakebook/__init__.py`** (MAY NEED UPDATE)

- Export `Bakebook` from `bakebook` submodule
- Consider exporting `BakebookType` alias if keeping it

### CLI Integration Files

**`src/bake/cli/bake/main.py`** (NEEDS UPDATE)

- Line 35: `bake_app.add_typer(bakefile_obj.bakebook)`
- Change to: `bake_app.add_typer(bakefile_obj.bakebook.to_typer())`

**`src/bake/cli/common/obj.py`** (NEEDS UPDATE)

- Line 48: `bakebook: BakebookType | None`
- Change to: `bakebook: Bakebook | None`

**`src/bake/__init__.py`** (NEEDS UPDATE)

- Add `Bakebook` to exports
- Update `__all__` list

### Test Files

**`tests/bake/bakebook/test_bakebook.py`** (TO BE CREATED)

- Unit tests for `Bakebook` class
- Test instantiation, command registration, env validation

**`tests/bake/bakebook/test_get.py`** (NEEDS UPDATE)

- Lines with `typer.Typer()` → `Bakebook()`
- Update isinstance assertions
- Update type hints

**`tests/bake/cli/common/test_obj.py`** (NEEDS UPDATE)

- Mock bakebook instances

**`tests/bake/cli/bake/test_bake_main.py`** (NEEDS UPDATE)

- Integration tests with new `Bakebook` class

### Example Files

**`examples/simple/bakefile.py`** (NEEDS UPDATE)

- Line 14: `import typer` → `from bake import Bakebook`
- Line 21: `bakebook = typer.Typer()` → `bakebook = Bakebook()`

**`src/bake/samples/simple.py`** (NEEDS UPDATE)

- Similar updates to examples

---

## Technical Constraints

### Pydantic Model Configuration

**Simplified:** No `model_config` needed! Using `PrivateAttr` bypasses all validation.

```python
from pydantic_settings import BaseSettings
from pydantic import PrivateAttr
import typer


class Bakebook(BaseSettings):
    _app: typer.Typer = PrivateAttr(default_factory=typer.Typer)
    # That's it! No ConfigDict needed.
```

**Why `PrivateAttr` instead of `Field(exclude=True)`:**

- No type validation (bypasses `arbitrary_types_allowed` requirement)
- Auto-excluded from serialization
- Private by convention (underscore prefix)
- Simpler and cleaner

**Why `BaseSettings` instead of `BaseModel`:**

- Automatic env var loading for user-defined fields
- Users define env vars directly on subclass
- No separate `env` field needed

### Typer Integration: `to_typer()` Method

```python
def to_typer(self) -> typer.Typer:
    """Return the internal Typer app for framework integration."""
    return self._app
```

**Why not `__call__()`:**

- Users don't call `bakebook()` directly
- Framework creates its own `bake_app` and calls that
- `to_typer()` is explicit and clear

**Usage in main.py:**

```python
bake_app.add_typer(bakefile_obj.bakebook.to_typer())
```

---

## Important Dependencies

### Pydantic Settings (Need to Verify)

**Check if installed:**

```bash
grep pydantic-settings pyproject.toml
```

**If not installed, need to add:**

```toml
dependencies = [
    "pydantic-settings>=2.0",
]
```

**Why needed:** `BaseSettings` class for environment validation

---

## Testing Strategy

### Unit Test Structure

```python
# tests/bake/bakebook/test_bakebook.py
class TestBakebook:
    def test_create_empty_bakebook():
        bakebook = Bakebook()
        assert bakebook.name == ""
        assert bakebook.env is None

    def test_bakebook_with_env():
        env = Env()
        bakebook = Bakebook(env=env)
        assert bakebook.env is env

    def test_command_registration():
        bakebook = Bakebook()
        @bakebook.command()
        def test_cmd():
            pass
        # Verify command registered

    def test_to_typer_returns_typer_instance():
        bakebook = Bakebook()
        assert isinstance(bakebook.to_typer(), typer.Typer)
```

### Integration Test Points

1. Load bakefile with `Bakebook` instance
2. Register commands via `@bakebook.command()`
3. Run commands via `bake` CLI
4. Verify context propagation
5. Test env validation

---

## Migration Path for Existing Code

### Files Using `BakebookType`

**Search pattern:**

```bash
grep -r "BakebookType" src/ tests/
```

**Replacement pattern:**

```python
# Before
from bake.bakebook.type import BakebookType

# After
from bake.bakebook.bakebook import Bakebook
```

### Files Using `typer.Typer()` for Bakebooks

**Search pattern:**

```bash
grep -r "typer.Typer()" tests/ examples/
```

**Replacement pattern:**

```python
# Before
import typer
bakebook = typer.Typer()

# After
from bake import Bakebook
bakebook = Bakebook()
```

---

## Quick Resume Instructions

### When Returning to This Task

1. **Read this file (context.md)** - Has all decisions and file info
2. **Check tasks.md** - See what's done and what's next
3. **Refer to plan.md** - For overall strategy and phases

### To Start Implementation

1. **Verify pydantic-settings is installed**

    ```bash
    grep pydantic-settings pyproject.toml
    ```

2. **Implement Phase 1** - Create `Bakebook` class
    - File: `src/bake/bakebook/bakebook.py`
    - Follow design in plan.md

3. **Implement Phase 2** - Write unit tests
    - File: `tests/bake/bakebook/test_bakebook.py`
    - Test all public methods

4. **Continue through phases** - Follow plan.md sequentially

5. **Run validation** - Phase 9: `make test && make lint`

---

## Common Issues and Solutions

### Issue: Pydantic ValidationError for `_app` field

**Symptom:** `ValidationError: Instance is not valid (should be a valid Typer instance)`

**Solution:** Ensure `arbitrary_types_allowed=True` in model_config

### Issue: `add_typer()` expects Typer, got Bakebook

**Symptom:** TypeError at main.py line 35

**Solution:** Use `bakebook.to_typer()` method

### Issue: Tests fail with isinstance checks

**Symptom:** `assert isinstance(bakebook, typer.Typer)` fails

**Solution:** Change to `assert isinstance(bakebook, Bakebook)`

---

## References

### Documentation

- `.dev/README.md` - Dev docs pattern (for context on this file structure)
- `.claude/BEST_PRACTICES.md` - Coding standards, bakebook patterns
- Plan: `.dev/active/13-bakebook-class/plan.md` - Full implementation plan

### External References

- [Pydantic BaseModel](https://docs.pydantic.dev/latest/concepts/models/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Typer CLI](https://typer.tiangolo.com/)

---

## Notes

- This task was discussed at length with the user before planning
- All key design decisions are finalized
- Ready for implementation when user gives go-ahead
- No backward compatibility constraints (POC project)
