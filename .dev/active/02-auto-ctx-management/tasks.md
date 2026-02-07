# Tasks: Auto Context Management for BaseSpace Commands

**Last Updated:** 2025-02-07

## Phase 1: Implementation

- [ ] **1.1** Add `_wrap_command_method()` to Bakebook class
    - **Effort**: S
    - **Acceptance**: Function exists, properly wraps methods with ctx parameter
    - **File**: `src/bake/bakebook/bakebook.py`

- [ ] **1.2** Add imports to bakebook.py
    - `import inspect`
    - `import functools`
    - `import types`
    - **Acceptance**: Imports added at top of file

## Phase 2: Integration

- [ ] **2.1** Modify `_register_marked_methods()` to use wrapper
    - **Effort**: S
    - **Acceptance**: Command methods are wrapped before registration
    - **File**: `src/bake/bakebook/bakebook.py`

## Phase 3: Testing

- [ ] **3.1** Run type checking
    - **Command**: `uv run ty check --error-on-warning --no-progress .`
    - **Acceptance**: All checks pass

- [ ] **3.2** Run unit tests
    - **Command**: `bake test`
    - **Acceptance**: All 1406 tests pass

- [ ] **3.3** Run linting
    - **Command**: `bake lint`
    - **Acceptance**: All checks pass

## Phase 4: Cleanup

- [ ] **4.1** Remove `_set_ctx` usage in `base.py`
    - **Methods to update**: `test()`, `test_integration()`, `test_all()`, `clean()`, `assert_setup_dev()`
    - **Effort**: M
    - **Acceptance**: No `with self._set_ctx(ctx):` in command methods
    - **File**: `src/bakelib/space/base.py`

- [ ] **4.2** Remove `_set_ctx` usage in `python.py`
    - **Methods to update**: `test()`, `test_all()`, `test_integration()`
    - **Effort**: S
    - **Acceptance**: No `with self._set_ctx(ctx):` in command methods
    - **File**: `src/bakelib/space/python.py`

- [ ] **4.3** Verify `_set_ctx` still exists (keep for edge cases)
    - **Acceptance**: `_set_ctx` method still available in BaseSpace

## Phase 5: Final Verification

- [ ] **5.1** Full test suite pass
    - **Command**: `bake test`
    - **Acceptance**: All tests pass

- [ ] **5.2** Full lint pass
    - **Command**: `bake lint`
    - **Acceptance**: All checks pass

- [ ] **5.3** Test a command manually (optional)
    - **Acceptance**: Command runs without errors

## Notes

- **Dependencies**: Task 1.1 must complete before 2.1
- **Testing**: Run tests after each phase to catch issues early
- **Rollback**: If tests fail, revert changes and debug

## Completion Criteria

✅ All tasks checked off
✅ All tests passing
✅ Lint passing
✅ No manual `_set_ctx` needed in command methods
