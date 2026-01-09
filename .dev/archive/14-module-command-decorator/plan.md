# Module-Level Command Decorator - Implementation Plan

**Last Updated: 2026-01-04**

---

## Executive Summary

**Goal:** Enable users to define Bakebook commands as class methods with access to instance properties.

**Problem:** Currently, `@bakebook.command()` only works on standalone functions. Users want to inherit from `Bakebook` and define methods as commands within the class, giving them access to instance properties via `self`.

**Solution:** Introduce a module-level `@bake.command()` decorator that marks methods during class definition, then auto-registers them when the Bakebook is instantiated.

**Impact:** Users can now create reusable, composable task runners with OOP patterns - methods can access environment variables, configuration, and helper methods via `self`.

---

## Current State

### Existing API

Users create standalone functions decorated with `@bakebook.command()`:

```python
from bake import Bakebook

bakebook = Bakebook()

@bakebook.command()
def build(prod: bool = False):
    """Build the project."""
    console.echo(f"Building{' (prod)' if prod else ''}...")
```

**Limitations:**

- No access to bakebook instance properties
- Cannot call helper methods on the bakebook
- Functions are "free-floating" - not part of an OOP structure

### Bakebook Class (v2 - current)

Users can inherit and add properties:

```python
from bake import Bakebook

class MyBakebook(Bakebook):
    database_url: str = "sqlite:///default.db"
    debug: bool = False

    def get_connection(self):
        """Helper method - NOT a command."""
        return connect(self.database_url)

bakebook = MyBakebook()
```

**Works for:**

- Environment variable loading (BaseSettings)
- Custom properties
- Helper methods

**Does NOT work:**

- Defining methods as commands
- `@bakebook.command()` requires instance before class definition

---

## Proposed Future State

### New API

Users can decorate methods directly in the class:

```python
from bake import Bakebook, command

class MyBakebook(Bakebook):
    database_url: str = "sqlite:///default.db"
    debug: bool = False

    @command()
    def migrate(self):
        """Run migrations - has access to self.database_url"""
        console.echo(f"Migrating {self.database_url}")

    @command(name="deploy-prod")
    def deploy(self):
        """Deploy the application"""
        if self.debug:
            console.echo("Debug mode - skipping deployment")
        else:
            console.echo("Deploying...")

    def helper_method(self):
        """Internal helper - NOT a command"""
        return "internal"

bakebook = MyBakebook()  # Commands auto-registered on instantiation
```

### Hybrid API (Both Work)

```python
from bake import Bakebook, command

bakebook = Bakebook()

# Old way: standalone functions (still works)
@bakebook.command()
def standalone_task():
    """This still works."""
    pass

# New way: class methods
class MyBakebook(Bakebook):
    @command()
    def method_task(self):
        """This is new."""
        pass
```

---

## Implementation Phases

### Phase 1: Create Decorator Module (Effort: S)

**Tasks:**

1. Create `src/bake/decorator.py` with `command()` function
2. Handle both `@command` and `@command()` syntax
3. Store decorator metadata on function attributes

**Acceptance:**

- `@command` marks function without calling it
- `@command(name="custom")` stores custom name
- `@command()` (no args) works
- Function remains callable (not modified during decoration)

**Files:**

- `src/bake/decorator.py` (new)

---

### Phase 2: Update Bakebook Initialization (Effort: M)

**Tasks:**

1. Add `_register_marked_methods()` to `Bakebook.__init__`
2. Scan instance methods for `_bake_command_*` attributes
3. Bind methods to instance and register with `_app`
4. Handle inheritance (scan parent classes)

**Acceptance:**

- Methods marked with `@command()` are registered as commands
- Commands have access to `self`
- Inheritance works (child can override parent commands)
- Private methods (starting with `_`) are skipped

**Files:**

- `src/bake/bakebook/bakebook.py`

---

### Phase 3: Export from Package (Effort: S)

**Tasks:**

1. Add `command` to `src/bake/__init__.py`
2. Update `__all__` list

**Acceptance:**

- `from bake import command` works
- `from bake import Bakebook, command` works
- IDE autocomplete shows `command`

**Files:**

- `src/bake/__init__.py`

---

### Phase 4: Tests (Effort: M)

**Tasks:**

1. Test basic method command registration
2. Test method has access to `self`
3. Test custom command names
4. Test inheritance (parent/child commands)
5. Test private methods not registered
6. Test hybrid API (both old and new work together)
7. Test `@command` vs `@command()` syntax

**Acceptance:**

- All test cases pass
- Coverage maintained or improved
- No regressions in existing tests

**Files:**

- `tests/bake/bakebook/test_bakebook.py`
- `tests/bake/decorator/test_decorator.py` (new)

---

### Phase 5: Documentation (Effort: M)

**Tasks:**

1. Update `.claude/BEST_PRACTICES.md` with examples
2. Update `.claude/PROJECT_KNOWLEDGE.md` if needed
3. Add example bakefile using new pattern
4. Update docstrings (if developer adds them)

**Acceptance:**

- Best practices document shows both APIs
- Example demonstrates `self` access
- Migration notes clear

**Files:**

- `.claude/BEST_PRACTICES.md`
- `.claude/PROJECT_KNOWLEDGE.md` (if needed)
- `examples/` (new example file)

---

## Detailed Task Breakdown

### Task 1.1: Create decorator.py module

**File:** `src/bake/decorator.py`

**Implementation:**

```python
from typing import Callable, Any

def command(*args, **kwargs) -> Callable:
    """Mark a method as a bakebook command.

    Usage:
        class MyBakebook(Bakebook):
            @command()
            def build(self):
                ...

    Args can be passed to customize the command:
        @command(name="custom-name", help="Custom help text")
        def build(self):
            ...
    """
    def decorator(func: Callable) -> Callable:
        func._bake_command_args = args
        func._bake_command_kwargs = kwargs
        return func

    if args and callable(args[0]):
        return decorator(args[0])
    return decorator
```

**Acceptance Criteria:**

- Function is returned unmodified (except for attributes)
- Both `@command` and `@command()` work
- Args/kwargs stored on function attributes

---

### Task 1.2: Add \_register_marked_methods to Bakebook

**File:** `src/bake/bakebook/bakebook.py`

**Changes:**

1. Add `__init__` method if not exists
2. Call `super().__init__(**kwargs)`
3. Call `self._register_marked_methods()`

**Implementation:**

```python
def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self._register_marked_methods()

def _register_marked_methods(self) -> None:
    """Register methods marked with @bake.command as commands."""
    for name in dir(self):
        if name.startswith('_'):
            continue

        attr = getattr(self, name)

        if hasattr(attr, '_bake_command_kwargs'):
            bound_method = getattr(self, name)
            cmd_args = getattr(attr, '_bake_command_args', ())
            cmd_kwargs = getattr(attr, '_bake_command_kwargs', {})
            self._app.command(*cmd_args, **cmd_kwargs)(bound_method)
```

**Acceptance Criteria:**

- Decorated methods are registered as commands
- Methods have access to `self`
- Private methods skipped

---

### Task 2.1: Update package exports

**File:** `src/bake/__init__.py`

**Changes:**

```python
from bake.bakebook.bakebook import Bakebook
from bake.cli.common.context import Context
from bake.cli.utils.version import _get_version
from bake.decorator import command

__version__ = _get_version()

__all__ = ["Bakebook", "Context", "command", "__version__"]
```

**Acceptance Criteria:**

- `from bake import command` works
- IDE autocomplete includes `command`

---

### Task 3.1: Add tests for decorator

**File:** `tests/bake/decorator/test_decorator.py` (new)

**Test cases:**

1. `test_command_marks_function` - Verify attributes are set
2. `test_command_with_no_parens` - Test `@command` syntax
3. `test_command_with_parens` - Test `@command()` syntax
4. `test_command_with_args` - Test `@command(name="custom")`

---

### Task 3.2: Add tests for Bakebook method registration

**File:** `tests/bake/bakebook/test_bakebook.py`

**Test cases:**

1. `test_method_command_registration` - Basic method as command
2. `test_method_has_access_to_self` - Verify `self` works
3. `test_custom_command_name` - `@command(name="custom")`
4. `test_inheritance` - Parent/child command behavior
5. `test_private_methods_not_registered` - `_private` skipped
6. `test_hybrid_api` - Both old and new work together

**Example test:**

```python
def test_method_command_registration():
    class MyBakebook(Bakebook):
        @command()
        def test_method(self):
            return "test"

    bakebook = MyBakebook()
    assert len(bakebook._app.registered_commands) > 0
```

---

## Risk Assessment

### Risks and Mitigation

| Risk                             | Probability | Impact | Mitigation                          |
| -------------------------------- | ----------- | ------ | ----------------------------------- |
| Method binding issues            | Medium      | Medium | Thorough testing of bound methods   |
| Inheritance edge cases           | Low         | Medium | Test MRO, parent/child override     |
| Performance (scanning dir())     | Low         | Low    | Only runs during initialization     |
| Confusion about which API to use | Medium      | Low    | Clear documentation, examples       |
| Typer signature preservation     | Low         | Medium | Verify Typer sees correct signature |

### Edge Cases to Handle

1. **Same method in parent and child**
    - Child's command overrides parent's (expected Python behavior)

2. **Property with same name as method**
    - Property takes precedence (already Python behavior)
    - Could add warning if detected

3. **Multiple instances**
    - Each instance re-registers commands
    - Usually fine - commands are idempotent in Typer
    - Document singleton pattern if needed

4. **Abstract base classes**
    - Commands register in whatever instance is created
    - No special handling needed

---

## Success Metrics

### Functional Requirements

- [x] `@bake.command()` decorator exists
- [x] Decorated methods are registered as commands
- [x] Methods have access to `self` (instance properties)
- [x] Custom command names work
- [x] Inheritance works correctly
- [x] Existing API (standalone functions) still works
- [x] All tests pass
- [x] Coverage maintained

### Non-Functional Requirements

- No performance regression in initialization
- Clear, intuitive API
- Backwards compatible
- Well-documented

---

## Required Resources and Dependencies

### Dependencies

- None (uses existing dependencies: typer, pydantic)

### Files to Modify

1. `src/bake/__init__.py`
2. `src/bake/bakebook/bakebook.py`

### Files to Create

1. `src/bake/decorator.py`
2. `tests/bake/decorator/__init__.py`
3. `tests/bake/decorator/test_decorator.py`
4. `examples/class-methods/bakefile.py` (optional)

### Documentation to Update

1. `.claude/BEST_PRACTICES.md`
2. `.claude/PROJECT_KNOWLEDGE.md` (if needed)

---

## Timeline Estimates

| Phase                     | Tasks       | Estimated Effort |
| ------------------------- | ----------- | ---------------- |
| Phase 1: Decorator Module | 1 task      | 30 minutes       |
| Phase 2: Bakebook Init    | 2 tasks     | 1 hour           |
| Phase 3: Package Exports  | 1 task      | 15 minutes       |
| Phase 4: Tests            | 2 tasks     | 1.5 hours        |
| Phase 5: Documentation    | 1 task      | 45 minutes       |
| **Total**                 | **7 tasks** | **~4 hours**     |

---

## Implementation Order

**Recommended sequence:**

1. **Phase 1** - Create decorator (test in isolation)
2. **Phase 2** - Update Bakebook (integrate decorator)
3. **Phase 3** - Export from package
4. **Phase 4** - Add comprehensive tests
5. **Phase 5** - Update documentation

**After each phase:** Run `make lint` and `make test` to verify.

---

## Design Decisions

### Why deferred registration?

**Alternative considered:** Class decorator `@bake.register`

**Rejected because:**

- Extra decorator users must remember
- Less intuitive than just `@bake.command()`
- Module-level decorator is more pythonic

**Chosen approach:** Store metadata on function, register in `__init__`

**Benefits:**

- Automatic (no manual registration step)
- Clean API
- Similar patterns in Flask/FastAPI

### Why keep existing API?

**Decision:** Hybrid approach - both APIs supported

**Rationale:**

- Backwards compatibility
- Different use cases:
    - Standalone functions: Simple tasks, no state
    - Class methods: Complex tasks with state/config
- User choice based on needs

### Why store on function attributes?

**Alternatives considered:**

1. Global registry (rejected: messy, import-order issues)
2. Class-level registry (rejected: requires class decorator)
3. Metaclass (rejected: overcomplicated)

**Chosen:** Function attributes (`_bake_command_*`)

**Benefits:**

- Simple
- Local to function
- No global state
- Works with inheritance

---

## Open Questions

1. **Should we support `@classmethod` or `@staticmethod`?**
    - Initial implementation: Instance methods only
    - Future: Could add support if requested

2. **Should we detect property/method collisions?**
    - Initial implementation: Let Python handle it
    - Future: Add warning if helpful

3. **Should we support method overriding documentation?**
    - Initial implementation: Rely on Typer's help
    - Future: Add if needed
