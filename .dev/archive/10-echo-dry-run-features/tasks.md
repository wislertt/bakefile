# Tasks: Echo and Dry-Run Features for Run Module

**Last Updated:** 2026-01-02 (Phase 1-5 complete)

## Checklist

### Phase 1: Update `run()` Function

- [x] **Task 1.1:** Add `echo` and `dry_run` parameters to main `run()` function signature
    - Set defaults: `echo=True`, `dry_run=False`
    - Place before `**kwargs`
    - Verify type hints are correct

- [x] **Task 1.2:** Update all 4 `@overload` signatures
    - Update overload for `str` + `capture_output=True`
    - Update overload for `str` + `capture_output=False`
    - Update overload for `list/tuple` + `capture_output=True`
    - Update overload for `list/tuple` + `capture_output=False`

- [x] **Task 1.3:** Implement echo logic
    - Add after `cmd_str` construction
    - Use lazy import: `from bake.ui import console`
    - Call `console.cmd(cmd_str)` when `echo=True`

- [x] **Task 1.4:** Implement dry_run logic
    - Add after echo logic
    - Return `CompletedProcess` with `returncode=0`
    - Respect `capture_output` in return value
    - Early return before subprocess execution

- [x] **Task 1.5:** Update `run()` docstring
    - Document `echo` parameter
    - Document `dry_run` parameter
    - Note that dry_run doesn't auto-echo
    - Add examples for all 4 combinations

- [x] **Task 1.6:** ⚠️ **CRITICAL VALIDATION**
    - Run `make lint` — ensure no linting errors
    - Run `make test` — ensure all existing tests pass
    - Verify new defaults (`echo=True`) don't break existing functionality
    - Only proceed to Phase 2 after validation passes

### Phase 2: Update `run_uv()` Function

- [x] **Task 2.1:** Add `echo` and `dry_run` parameters to `run_uv()` function signature
    - Set defaults: `echo=True`, `dry_run=False`
    - Place before `**kwargs`
    - Update both overload signatures

- [x] **Task 2.2:** Implement echo logic in `run_uv()`
    - Build display string: `"uv " + " ".join(cmd)`
    - Use lazy import: `from bake.ui import console`
    - Call `console.cmd(display_cmd)` when `echo=True`
    - Ensure only "uv" prefix shows, not full binary path

- [x] **Task 2.3:** Implement dry_run logic in `run_uv()`
    - Return `CompletedProcess` with `returncode=0`
    - Respect `capture_output` in return value
    - Early return before calling `run()`

- [x] **Task 2.4:** Update `run_uv()` to call `run()` properly
    - Pass full uv binary path: `[uv_bin, *cmd]`
    - Set `echo=False` (prevent double display)
    - Pass through all other parameters

- [x] **Task 2.5:** Update `run_uv()` docstring
    - Document `echo` parameter with "uv" prefix note
    - Document `dry_run` parameter
    - Add examples showing display output

- [x] **Task 2.6:** ⚠️ **CRITICAL VALIDATION**
    - Run `make lint` — ensure no linting errors
    - Run `make test` — ensure all tests pass
    - Verify echo displays "uv" prefix only (not full path)
    - Only proceed to Phase 3 after validation passes

### Phase 3: Implement `run_script()` Function

- [x] **Task 3.1:** Create `run_script()` function signature
    - Add after `run()` function
    - Include all explicit params: `title, script, capture_output, check, cwd, stream, echo, dry_run`
    - Add `**kwargs` for additional subprocess args
    - No `shell` parameter (always `True`)

- [x] **Task 3.2:** Implement echo logic in `run_script()`
    - Use lazy import: `from bake.ui import console`
    - Call `console.script_block(title, script)` when `echo=True`

- [x] **Task 3.3:** Implement dry_run logic in `run_script()`
    - Return `CompletedProcess` with `returncode=0`
    - Respect `capture_output` in return value
    - Early return before calling `run()`

- [x] **Task 3.4:** Call `run()` from `run_script()`
    - Pass all matching params explicitly
    - Set `echo=False` (prevent double display)
    - Set `shell=True` (always shell for scripts)
    - Pass `**kwargs` for additional args

- [x] **Task 3.5:** Write comprehensive docstring for `run_script()`
    - Describe purpose (multi-line shell scripts)
    - Document all parameters
    - Note `shell=True` is implicit
    - Add practical examples

### Phase 4: Update Tests

- [x] **Task 4.1:** Add `TestRunScript` class to `tests/bake/ui/run/test_script.py`
    - Created separate test file `test_script.py`
    - Tests: Basic execution, echo + dry_run combinations, capture_output=False, multi-line scripts
    - Uses `@pytest.mark.parametrize` for echo/dry_run combinations
    - No unnecessary `setup_logging` calls (only capturing console output)

- [x] **Task 4.2:** Run full test suite
    - Run `make test` — 649 tests pass, 93% coverage
    - Run `make lint` — All checks passed
    - `script.py` has 100% coverage

### Phase 5: Update Documentation

- [x] **Task 5.1:** Update `.claude/PROJECT_KNOWLEDGE.md`
    - Added "Command Execution" section with `run()`, `run_script()`, `run_uv()` docs
    - Documented echo and dry_run parameters
    - Added practical examples for all functions

- [x] **Task 5.2:** Update `.claude/BEST_PRACTICES.md` (if needed)
    - No additional best practices needed — usage is straightforward

### Phase 6: Integration and Validation

- [ ] **Task 6.1:** Verify no circular dependencies
    - Check `bake.ui.run` imports don't create cycles
    - Verify lazy import of `console` works

- [ ] **Task 6.2:** Manual testing
    - Test `run()` with various commands
    - Test `run_uv()` with various uv commands
    - Test `run_script()` with multi-line scripts
    - Test echo/dry_run combinations
    - Verify PTY/color behavior still works

- [ ] **Task 6.3:** Performance check
    - Verify `run()` performance is unchanged
    - Check that echo doesn't add significant overhead
    - Profile dry-run path (should be fast)

- [ ] **Task 6.4:** Final validation
    - Run `make test` — all tests pass
    - Run `make lint` — no new issues
    - Manual verification of all features

## Summary

**Total Tasks:** 23 (reduced from 27)

**Progress:** 19/23 (83%)

**Completed:**

- ✅ Phase 1: Update `run()` Function (6/6 tasks)
- ✅ Phase 2: Update `run_uv()` Function (6/6 tasks)
- ✅ Phase 3: Implement `run_script()` Function (5/5 tasks)
- ✅ Phase 4: Update Tests (2/2 tasks)
- ✅ Phase 5: Update Documentation (2/2 tasks)

**Next Task:** Task 6.1 — Verify no circular dependencies
