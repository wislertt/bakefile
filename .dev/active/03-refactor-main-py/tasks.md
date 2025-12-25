# Refactor main.py - Task Checklist

**Last Updated:** 2025-12-25

---

## Phase 1: Remove Debug Code ⏳ NOT STARTED

**Effort:** S (5 minutes)

- [ ] Remove `print("start bake")` from `_bake` function (line 25)
- [ ] Remove `print("get bakebook")` from `_bake` function (line 28)
- [ ] Run tests: `python -m pytest tests/cli/bake/test_main.py -v`
- [ ] Run linting: `make lint`

---

## Phase 2: Remove `_bake` Abstraction ⏳ NOT STARTED

**Effort:** S (5 minutes)

- [ ] Replace `_bake(chdir=chdir, file_name=file_name, bakebook_name=bakebook_name)` with direct `resolve_bakebook(chdir=chdir, file_name=file_name, bakebook_name=bakebook_name)` in `get_bakebook` function
- [ ] Remove `_bake` function entirely (lines 24-29)
- [ ] Run tests: `python -m pytest tests/cli/bake/test_main.py -v`
- [ ] Run linting: `make lint`

---

## Phase 3: Extract Shared Callback Logic ⏳ NOT STARTED

**Effort:** S (10 minutes)

- [ ] Create `show_help_if_no_command(ctx: typer.Context)` function above callbacks
- [ ] Update `local_bake_app_callback` to call `show_help_if_no_command(ctx)`
- [ ] Update `bake_app_callback` to call `show_help_if_no_command(ctx)`
- [ ] Run tests: `python -m pytest tests/cli/bake/test_main.py -v`
- [ ] Run linting: `make lint`

---

## Phase 4: Fix `version` Parameter Handling ⏳ NOT STARTED

**Effort:** S (5 minutes)

- [ ] Remove `_ = version` line (line 99)
- [ ] Keep `version` parameter (needed for Typer to process `--version` option)
- [ ] Add comment explaining why version is unused in function body
- [ ] Run tests: `python -m pytest tests/cli/bake/test_main.py -v`
- [ ] Run linting: `make lint`

---

## Phase 5: Evaluate Option Consolidation ⏳ NOT STARTED

**Effort:** M (15-30 minutes)

### 5.1: Research

- [ ] Research Typer best practices for shared options
- [ ] Check if Typer supports option factories or shared definitions
- [ ] Test type checking implications of shared options

### 5.2: Decision

- [ ] Document findings in context.md
- [ ] **If viable:** Implement shared options factory
- [ ] **If not viable:** Document why current duplication is acceptable

### 5.3: Implementation (if pursuing)

- [ ] Create `_create_common_options()` factory function
- [ ] Update all three function signatures to use shared options
- [ ] Add type: ignore comments if needed
- [ ] Run tests: `python -m pytest tests/cli/bake/test_main.py -v`
- [ ] Run linting: `make lint`
- [ ] Run type checking: `uv run ty check`

---

## Verification Phase ⏳ NOT STARTED

**Effort:** M (10 minutes)

- [ ] Run all tests: `python -m pytest tests/ -v`
- [ ] Run linting: `make lint`
- [ ] Run type checking: `uv run ty check`
- [ ] Manual testing: `bake --help`, `bake --version`, `bake -C examples/simple`
- [ ] Check for any remaining duplication or code smells

---

## Completion Criteria

- [ ] All 5 phases completed (or Phase 5 documented as not viable)
- [ ] All tests pass
- [ ] No linting errors
- [ ] No new type checking errors
- [ ] Code is self-documenting (fewer comments needed)
- [ ] Dev docs moved to `.dev/archive/03-refactor-main-py/`

---

## Notes

- **Acceptance Criteria:** Each task must pass tests and linting before proceeding
- **Phase 5 is optional** - may document that current duplication is acceptable given Typer constraints
- **Update this file** as you complete tasks (mark with [x])

**Quick Resume:** Start with Phase 1, work through sequentially, update context.md SESSION PROGRESS after each phase
