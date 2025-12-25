# Refactor main.py - Context

**Last Updated:** 2025-12-25

---

## SESSION PROGRESS (2025-12-25)

### ✅ COMPLETED

- Dev docs structure created (plan, context, tasks files)
- Analysis of current state completed
- Implementation plan documented

### 🟡 IN PROGRESS

- Awaiting user approval to begin implementation
- Phase 1-4 are straightforward, Phase 5 needs evaluation

### ⚠️ BLOCKERS

- None currently

---

## Key Files

### `src/bakefile/cli/bake/main.py` (PRIMARY TARGET)

**Current structure:**

- **Lines 10-18:** Two Typer app instances (`bake_app`, `local_bake_app`)
- **Lines 24-29:** `_bake()` wrapper function with debug prints
- **Lines 32-51:** `local_bake_app_callback` - callback for local bake app
- **Lines 54-73:** `bake_app_callback` - callback for base bake app
- **Lines 76-100:** `get_bakebook` command - hidden command that loads bakebook
- **Lines 103-120:** `try_get_local_bake_app()` - tries to load local bakebook, falls back if fails
- **Lines 123-128:** `main()` - entry point that loads bakebook or falls back to `bake_app()`

**Key insights:**

- The two apps (`bake_app` and `local_bake_app`) serve different purposes:
    - `bake_app`: Base/fallback app with the `get_bakebook` hidden command
    - `local_bake_app`: Receives the user's bakebook as a sub-app and runs it
- `try_get_local_bake_app()` attempts to call the hidden `get_bakebook` command programmatically
- If bakebook loading fails, `main()` falls back to showing `bake_app` help

### `src/bakefile/cli/bake/utils.py`

**Purpose:** Utilities for argument processing

**Key function:**

- `get_bakebook_args()` - Filters `--help` and `--version` from args before command invocation

**Important:** `--help` and `--version` are filtered out here because they're handled by the callback (eager option for version).

### `src/bakefile/cli/bake/resolve_bakebook.py`

**Purpose:** Load and validate bakebook from user's bakefile.py

**Key functions:**

- `resolve_bakebook()` - Main entry point for bakebook resolution
- `change_directory()` - Changes to specified directory
- `validate_file_name()` - Validates filename format
- `resolve_file_path()` - Resolves file path
- `load_module()` - Loads Python module dynamically
- `get_bakebook()` - Retrieves bakebook object from module
- `validate_bakebook()` - Validates bakebook is typer.Typer

**Errors:** Raises `BakebookError` (from `src/bakefile/exceptions.py`) on validation failure

### `src/bakefile/exceptions.py`

**Purpose:** Custom exceptions for bakefile

**Classes:**

- `BaseBakefileError` - Base exception for all bakefile errors
- `BakebookError(BaseBakefileError)` - Raised when bakebook cannot be loaded/validated

### `src/bakefile/cli/utils/version.py`

**Purpose:** Version callback for `--version` option

**Key function:**

- `version_callback(value: bool)` - Prints version and exits with `typer.Exit()`

---

## Important Decisions

### Decision 1: Keep Two Separate Apps (2025-12-25)

**Question:** Should we consolidate `bake_app` and `local_bake_app` into a single app?

**Decision:** NO - keep them separate.

**Rationale:**

- They serve different purposes (fallback vs user's bakebook)
- The current architecture allows graceful fallback when bakebook loading fails
- `local_bake_app` dynamically receives the user's bakebook as a sub-app via `add_typer()`

### Decision 2: Option Duplication May Be Acceptable (2025-12-25)

**Question:** Should we aggressively eliminate option duplication using a factory pattern?

**Decision:** PARTIAL - extract callback logic first, evaluate option sharing later.

**Rationale:**

- Typer expects `typer.Option()` directly in function signatures for proper type checking
- Factory pattern may break IDE autocomplete and type hints
- Callback logic duplication is easier to extract without side effects

---

## Technical Constraints

### Typer Framework Constraints

1. **Options must be defined inline** - Typer's type system relies on decorators and function signatures
2. **`callback` and `is_eager` parameters** must be on the `typer.Option()` call itself
3. **Context parameter** must be first parameter in callbacks for `invoke_without_command=True`

### Project Best Practices

From `.claude/BEST_PRACTICES.md`:

- Use `bakebook` as the variable name (not `bakebook_app`, etc.)
- Omit docstrings for self-explanatory functions
- Use NumPy-style docstrings for functions with multiple parameters
- Tests mirror source folder structure

---

## Dependencies

### Internal Dependencies

```
main.py depends on:
├── bakefile.cli.bake.resolve_bakebook (resolve_bakebook)
├── bakefile.cli.utils.version (version_callback)
├── bakefile.exceptions (BakebookError)
└── .utils (get_bakebook_args)
```

### External Dependencies

- **typer** - CLI framework
- **click** - Underlying CLI library (used by typer)

---

## Quick Resume

To continue refactoring:

1. Start with **Phase 1** (Remove Debug Code) - safest, easiest
2. Proceed through **Phases 2-4** in order
3. Pause before **Phase 5** to evaluate if option consolidation is worth pursuing
4. Run `make test && make lint` after each phase
5. Update this file's SESSION PROGRESS as you complete tasks

**Testing command:** `python -m pytest tests/cli/bake/test_main.py -v`

**Linting command:** `make lint`
