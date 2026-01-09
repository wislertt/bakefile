# Module-Level Command Decorator - Task Checklist

**Last Updated: 2026-01-04**

---

## Phase 1: Create Decorator Module ✅

**Effort:** 30 minutes | **Status:** Complete

- [x] **Task 1.1:** Create `src/bake/bakebook/decorator.py` module
    - [x] Implement `command()` function
    - [x] Handle `@command` syntax (no parens)
    - [x] Handle `@command()` syntax (with parens)
    - [x] Handle `@command(name="custom")` (with args)
    - [x] Store metadata on function attributes (`_bake_command_args`, `_bake_command_kwargs`)
    - [x] Return function unmodified (except attributes)
    - **Acceptance:** Decorator marks functions without calling them; both syntaxes work

---

## Phase 2: Update Bakebook Initialization ✅

**Effort:** 1 hour | **Status:** Complete

- [x] **Task 2.1:** Add `__init__` method to `Bakebook` class
    - [x] Create `__init__(self, **kwargs)` method
    - [x] Call `super().__init__(**kwargs)` for Pydantic initialization
    - [x] Call `self._register_marked_methods()` after super init
    - **Acceptance:** Bakebook can be instantiated; env vars still load

- [x] **Task 2.2:** Implement `_register_marked_methods()` method
    - [x] Create `_register_marked_methods(self) -> None` method
    - [x] Iterate through `dir(self)` to find instance attributes
    - [x] Skip private attributes (starting with `_`)
    - [x] Check for `_bake_command_kwargs` attribute
    - [x] Get bound method using `getattr(self, name)`
    - [x] Retrieve stored args/kwargs from function attributes
    - [x] Register with `self._app.command(*args, **kwargs)(bound_method)`
    - **Acceptance:** Decorated methods are registered as commands; methods have access to `self`

---

## Phase 3: Export from Package ✅

**Effort:** 15 minutes | **Status:** Complete

- [x] **Task 3.1:** Update `src/bake/__init__.py`
    - [x] Import `command` from `bake.bakebook.decorator`
    - [x] Add `command` to `__all__` list
    - **Acceptance:** `from bake import command` works; IDE autocomplete includes `command`

---

## Phase 4: Write Tests ✅

**Effort:** 1.5 hours | **Status:** Complete

- [x] **Task 4.1:** Create `tests/bake/bakebook/decorator/test_decorator.py`
    - [x] Create test directory structure
    - [x] Test: `test_command_marks_function` - Verify attributes are set
    - [x] Test: `test_command_with_no_parens` - `@command` syntax
    - [x] Test: `test_command_with_parens` - `@command()` syntax
    - [x] Test: `test_command_with_args` - `@command(name="custom")`
    - **Acceptance:** All decorator tests pass

- [x] **Task 4.2:** Add tests to `tests/bake/bakebook/test_bakebook.py`
    - [x] Test: `test_method_command_registration` - Basic method registration
    - [x] Test: `test_method_has_access_to_self` - Verify `self` works in methods
    - [x] Test: `test_custom_command_name` - `@command(name="custom")` works
    - [x] Test: `test_inheritance` - Parent/child command behavior
    - [x] Test: `test_private_methods_not_registered` - `_private` skipped
    - [x] Test: `test_hybrid_api` - Both old and new APIs work together
    - [x] Test: `test_standalone_function_still_works` - Regression test
    - **Acceptance:** All new tests pass; no regressions

- [x] **Task 4.3:** Run full test suite
    - [x] Run `make test`
    - [x] Verify coverage maintained
    - [x] Fix any failing tests
    - **Acceptance:** All tests pass; coverage OK (711 tests pass, 94% coverage)

---

## Phase 5: Update Documentation ✅

**Effort:** 45 minutes | **Status:** Complete

- [x] **Task 5.1:** Update `.claude/BEST_PRACTICES.md`
    - [x] Add "Class Methods as Commands" subsection
    - [x] Include basic usage example
    - [x] Include custom command name example
    - [x] Include helper method example
    - [x] Document key points
    - **Acceptance:** Best practices show both APIs with examples

- [x] **Task 5.2:** Update `.claude/PROJECT_KNOWLEDGE.md` (if needed)
    - [x] Review if updates needed for architecture documentation
    - [x] Add method command pattern if relevant
    - **Acceptance:** Architecture docs reflect new feature

- [x] **Task 5.3:** Create example bakefile (optional)
    - [x] Create `examples/class-methods/bakefile.py`
    - [x] Demonstrate `@bake.command()` on methods
    - [x] Show `self` access to properties
    - [x] Show helper methods vs commands
    - **Acceptance:** Example demonstrates new pattern

---

## Verification Steps ✅

**Status:** Complete

- [x] Run `make lint` - Check code quality (ruff passes)
- [x] Run `make test` - Verify all tests pass (711 tests pass)
- [x] Manual test with example bakefile
- [x] Verify backwards compatibility (standalone functions still work)
- [x] Check IDE autocomplete shows `command`
- [x] Verify imports work: `from bake import command`

---

## Summary

**Total Tasks:** 13
**Estimated Total Effort:** ~4 hours
**Actual Effort:** ~2 hours

**Phase Progress:**

- Phase 1: 1/1 completed (100%)
- Phase 2: 2/2 completed (100%)
- Phase 3: 1/1 completed (100%)
- Phase 4: 3/3 completed (100%)
- Phase 5: 3/3 completed (100%)
- Verification: 6/6 completed (100%)

**Overall Progress:** 13/13 tasks completed (100%)

---

## Quick Reference

### Files Created

1. `src/bake/bakebook/decorator.py`
2. `tests/bake/bakebook/decorator/__init__.py`
3. `tests/bake/bakebook/decorator/test_decorator.py`
4. `examples/class-methods/bakefile.py`

### Files Modified

1. `src/bake/bakebook/bakebook.py`
2. `src/bake/__init__.py`
3. `tests/bake/bakebook/test_bakebook.py`
4. `.claude/BEST_PRACTICES.md`

### Implementation Order

1. Phase 1 → 2 → 3 → 4 → 5
2. Ran `make lint` after each phase
3. Ran `make test` after Phase 4

### Success Criteria

- [x] `from bake import command` works
- [x] `@bake.command()` decorates methods
- [x] Methods have access to `self`
- [x] Inheritance works
- [x] Existing API still works
- [x] All tests pass
- [x] Documentation updated
