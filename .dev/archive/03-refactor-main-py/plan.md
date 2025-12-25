# Refactor main.py - Remove Redundancy and Improve Structure

**Last Updated:** 2025-12-25

---

## Executive Summary

Refactor `src/bakefile/cli/bake/main.py` to eliminate code duplication, improve maintainability, and align with project best practices. The current implementation has significant redundancy with 3 identical copies of the same 4 Typer options across different functions.

**Key Improvements:**

- Extract shared option definitions to a single source
- Create shared callback logic for help display
- Remove debug print statements
- Remove unnecessary abstraction layers
- Improve code readability and maintainability

---

## Current State Analysis

### Issues Identified

#### 1. Duplicate Option Definitions (3 copies)

The same 4 options are defined identically in three places:

| Location                  | Lines | Options                                  |
| ------------------------- | ----- | ---------------------------------------- |
| `local_bake_app_callback` | 37-48 | chdir, file_name, bakebook_name, version |
| `bake_app_callback`       | 59-70 | chdir, file_name, bakebook_name, version |
| `get_bakebook` command    | 86-97 | chdir, file_name, bakebook_name, version |

**Impact:** 69 lines of duplicated option definitions. Any change requires updating 3 places.

#### 2. Duplicate Callback Logic

Both callbacks execute identical code:

```python
if ctx.invoked_subcommand is None:
    typer.echo(ctx.get_help())
```

**Impact:** 8 lines duplicated, maintenance burden.

#### 3. Debug Print Statements

Lines 25 and 28 contain debug prints:

```python
print("start bake")
print("get bakebook")
```

**Impact:** Unwanted output in production, not following logging best practices.

#### 4. Unnecessary Abstraction

The `_bake` function (lines 24-29) wraps `resolve_bakebook` with debug prints but adds no value.

**Impact:** Unnecessary indirection, harder to understand data flow.

#### 5. Unused Variable Handling

Line 99: `_ = version` - underscore prefix indicates intentional non-use, but this pattern is unclear.

---

## Proposed Future State

### Option 1: Shared Options Factory (Recommended)

Create a factory function that returns option definitions:

```python
def _create_common_options():
    """Return common option definitions for bakebook commands."""
    return {
        "chdir": typer.Option(None, "-C", "--chdir", help="Change directory before running"),
        "file_name": typer.Option("bakefile.py", "--file-name", "-f", help="Path to bakefile.py"),
        "bakebook_name": typer.Option("bakebook", "--book-name", "-b", help="Name of bakebook object to retrieve"),
        "version": typer.Option(False, "--version", help="Show version and exit", callback=version_callback, is_eager=True),
    }

COMMON_OPTIONS = _create_common_options()
```

Then use unpacking in function signatures:

```python
def local_bake_app_callback(ctx: typer.Context, **_options: COMMON_OPTIONS):
    show_help_if_no_command(ctx)
```

**Benefits:**

- Single source of truth for option definitions
- Easy to add/modify options
- Clearer intent

**Drawbacks:**

- Non-standard Typer pattern (Typer expects direct `typer.Option()` calls)
- Type checking may be affected
- IDE autocomplete may not work as well

### Option 2: Shared Callback Function (Alternative)

Extract the duplicate callback logic:

```python
def show_help_if_no_command(ctx: typer.Context) -> None:
    """Show help when no subcommand is invoked."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
```

This is a cleaner extraction that maintains Typer's standard patterns.

**Benefits:**

- Standard Python function
- Type-safe
- Works with IDE autocomplete
- Follows DRY principle

---

## Implementation Phases

### Phase 1: Remove Debug Code (Effort: S)

**Acceptance:** No print statements remain, tests still pass

- [ ] Remove `print("start bake")` from `_bake` function
- [ ] Remove `print("get bakebook")` from `_bake` function
- [ ] Run tests to verify no regression

### Phase 2: Remove `_bake` Abstraction (Effort: S)

**Acceptance:** `resolve_bakebook` called directly from `get_bakebook`

- [ ] Replace `_bake(...)` call with direct `resolve_bakebook(...)` in `get_bakebook`
- [ ] Remove `_bake` function entirely
- [ ] Run tests to verify

### Phase 3: Extract Shared Callback Logic (Effort: S)

**Acceptance:** Single callback function used by both `local_bake_app_callback` and `bake_app_callback`

- [ ] Create `show_help_if_no_command(ctx: typer.Context)` function
- [ ] Update `local_bake_app_callback` to use shared function
- [ ] Update `bake_app_callback` to use shared function
- [ ] Run tests to verify

### Phase 4: Fix `version` Parameter Handling (Effort: S)

**Acceptance:** Version parameter properly handled without `_` pattern

- [ ] Remove `_ = version` line
- [ ] Keep version parameter (needed for Typer to process the option)
- [ ] Run tests to verify

### Phase 5: Evaluate Option Consolidation (Effort: M)

**Acceptance:** Decision made on whether to consolidate options

- [ ] Research Typer best practices for shared options
- [ ] Evaluate if Option 1 (shared options factory) is viable
- [ ] Decide based on findings:
    - **If viable:** Implement shared options
    - **If not viable:** Document why current duplication is acceptable (Typer limitation)

---

## Risk Assessment and Mitigation Strategies

| Risk                                     | Likelihood | Impact | Mitigation                             |
| ---------------------------------------- | ---------- | ------ | -------------------------------------- |
| Breaking existing tests                  | Low        | High   | Run full test suite after each phase   |
| Typer doesn't support option sharing     | Medium     | Low    | Phase 5 evaluation will determine this |
| Type checking breaks with shared options | Low        | Medium | Use type: ignore comments if needed    |
| IDE autocomplete affected                | Low        | Low    | Acceptable trade-off for DRY           |

---

## Success Metrics

1. **Code Reduction:** Target 30-40% reduction in lines of code
2. **Duplication Eliminated:** Zero duplicated option definitions or callback logic
3. **Tests Passing:** All existing tests pass without modification
4. **Type Checking:** No new type errors
5. **Documentation:** Code is self-documenting, fewer comments needed

---

## Required Resources and Dependencies

### Files to Modify

- `src/bakefile/cli/bake/main.py` (primary)

### Files to Read (for context)

- `src/bakefile/cli/bake/utils.py` - understand `get_bakebook_args`
- `src/bakefile/cli/bake/resolve_bakebook.py` - understand bakebook loading
- `src/bakefile/exceptions.py` - understand error handling
- `src/bakefile/cli/utils/version.py` - understand version callback

### Test Files to Run

- `tests/cli/bake/test_main.py` - main CLI tests
- `tests/cli/bake/test_resolve_bakebook.py` - bakebook resolution tests
- All other tests to ensure no regression

### External Dependencies

- None (refactoring only, no new dependencies)

---

## Timeline Estimates

| Phase                                     | Effort | Estimate          |
| ----------------------------------------- | ------ | ----------------- |
| Phase 1: Remove Debug Code                | S      | 5 minutes         |
| Phase 2: Remove `_bake` Abstraction       | S      | 5 minutes         |
| Phase 3: Extract Shared Callback Logic    | S      | 10 minutes        |
| Phase 4: Fix `version` Parameter Handling | S      | 5 minutes         |
| Phase 5: Evaluate Option Consolidation    | M      | 15-30 minutes     |
| **Total**                                 |        | **40-55 minutes** |

---

## Open Questions

1. Should we pursue Option 1 (shared options factory) given potential type checking implications?
2. Is the current level of option duplication acceptable given Typer's design constraints?
3. Should we consider restructuring the entire CLI to use a different pattern?

---

## References

- `.claude/BEST_PRACTICES.md` - Project coding standards
- `.claude/PROJECT_KNOWLEDGE.md` - Architecture overview
- Typer documentation: https://typer.tiangolo.com/
