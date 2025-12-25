# Refactor main.py - Task Checklist

**Last Updated:** 2025-12-25

---

## Phase 1: Remove Debug Code ✅ COMPLETED

**Effort:** S (5 minutes)

- [x] Remove `print("start bake")` from `_bake` function (line 25)
- [x] Remove `print("get bakebook")` from `_bake` function (line 28)
- [x] Run tests: `python -m pytest tests/cli/bake/test_main.py -v`
- [x] Run linting: `make lint`

---

## Phase 2: Remove `_bake` Abstraction ✅ COMPLETED

**Effort:** S (5 minutes)

- [x] Replace `_bake(chdir=chdir, file_name=file_name, bakebook_name=bakebook_name)` with direct `resolve_bakebook(chdir=chdir, file_name=file_name, bakebook_name=bakebook_name)` in `get_bakebook` function
- [x] Remove `_bake` function entirely (lines 24-29)
- [x] Run tests: `python -m pytest tests/cli/bake/test_main.py -v`
- [x] Run linting: `make lint`

---

## Phase 3: Extract Shared Callback Logic ✅ COMPLETED

**Effort:** S (10 minutes)

- [x] Create `show_help_if_no_command(ctx: typer.Context)` function above callbacks
- [x] Update `local_bake_app_callback` to call `show_help_if_no_command(ctx)`
- [x] Update `bake_app_callback` to call `show_help_if_no_command(ctx)`
- [x] Run tests: `python -m pytest tests/cli/bake/test_main.py -v`
- [x] Run linting: `make lint`

---

## Phase 4: Fix `version` Parameter Handling ✅ COMPLETED

**Effort:** S (5 minutes)

- [x] Keep `version` parameter (needed for Typer to process `--version` option)
- [x] Add comment explaining why version is unused in function body
- [x] Run tests: `python -m pytest tests/cli/bake/test_main.py -v`
- [x] Run linting: `make lint`

---

## Phase 5: Evaluate Option Consolidation ✅ COMPLETED

**Effort:** M (15-30 minutes)

### 5.1: Research

- [x] Research Typer best practices for shared options
- [x] Check if Typer supports option factories or shared definitions
- [x] Test type checking implications of shared options

### 5.2: Decision

- [x] Document findings in context.md
- [x] **Documented:** Current duplication is acceptable due to Typer constraints (see context.md Decision 3)

### 5.3: Implementation

- [N/A] Not pursued - determined not viable

---

## Verification Phase ✅ COMPLETED

**Effort:** M (10 minutes)

- [x] Run all tests: `python -m pytest tests/ -v` - 34 tests passed
- [x] Run linting: `make lint` - All checks passed
- [x] Run type checking: `uv run ty check` - All checks passed
- [x] Manual testing: `bake --help`, `bake --version`, `bake -C examples/simple` - All working
- [x] Check for any remaining duplication or code smells - Only acceptable duplication (Typer constraints)

---

## Completion Criteria

- [x] All 5 phases completed (or Phase 5 documented as not viable)
- [x] All tests pass
- [x] No linting errors
- [x] No new type checking errors
- [x] Code is self-documenting (fewer comments needed)
- [ ] Dev docs moved to `.dev/archive/03-refactor-main-py/`

---

## Summary

**Refactoring Complete!** All 5 phases successfully completed:

1. ✅ Removed debug print statements from `_bake` function
2. ✅ Removed `_bake` abstraction, using `resolve_bakebook` directly
3. ✅ Extracted shared callback logic into `show_help_if_no_command()` function
4. ✅ Fixed `version` parameter handling with proper documentation
5. ✅ Evaluated option consolidation - documented as not viable due to Typer constraints

**Code Quality Metrics:**

- Reduced code duplication by extracting callback logic
- Removed unnecessary abstraction layer
- Eliminated debug print statements
- Added clear documentation for version parameter handling
- All tests pass (34/34)
- No linting errors
- No type checking errors

---

## Notes

- **Acceptance Criteria:** Each task must pass tests and linting before proceeding
- **Phase 5 result:** Documented that current duplication is acceptable given Typer constraints (see context.md Decision 3)
- **Next step:** Archive dev docs to `.dev/archive/03-refactor-main-py/`

**Quick Resume:** All phases complete. Ready to archive dev docs.
