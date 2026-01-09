# Dry Run Flag - COMPLETED

**Completed:** 2025-01-04

---

## Summary

Added `--dry-run` / `-n` flag to both `bake` and `bakefile` CLIs. Users can now access dry run state via `ctx.obj.dry_run` in their bakefile commands.

---

## What Was Completed

### Phase 1: Core Infrastructure ✅

1. **Added `dry_run_option` to params.py** (`src/bake/cli/common/params.py:64-67`)

    ```python
    dry_run_option = Annotated[
        bool,
        typer.Option("-n", "--dry-run", help="Dry run (show what would be done without executing)"),
    ]
    ```

2. **Added `dry_run` field to BakefileObject** (`src/bake/cli/common/obj.py:50`)

    ```python
    @dataclass
    class BakefileObject:
        ...
        dry_run: bool = False
    ```

3. **Added `dry_run` parameter to `_get_bakefile_object`** (`src/bake/cli/common/obj.py:130`)

    ```python
    def _get_bakefile_object(
        ctx: typer.Context,
        ...
        dry_run: dry_run_option = False,
    ):
        return BakefileObject(..., dry_run=dry_run)
    ```

4. **Added `dry_run` property to Context** (`src/bake/cli/common/context.py:9-11`)

    ```python
    class Context(typer.Context):
        obj: BakefileObject

        @property
        def dry_run(self) -> bool:
            return self.obj.dry_run
    ```

5. **Added `_dry_run` parameter to `bake_app_callback`** (`src/bake/cli/common/app.py:43`)

    ```python
    def bake_app_callback(
        ctx: Context,
        ...
        _dry_run: dry_run_option = False,
    ):
    ```

6. **Updated imports** in `app.py` and `obj.py`

### Phase 2: Testing ✅

Added comprehensive tests:

1. **Unit tests for flag parsing** (`tests/bake/cli/common/test_obj.py`)
    - `test_get_bakefile_object_dry_run_default_is_false`
    - `test_get_bakefile_object_dry_run_with_long_flag`
    - `test_get_bakefile_object_dry_run_with_short_flag`

2. **Property tests** (`tests/bake/cli/common/test_context.py`)
    - `test_dry_run_property_returns_obj_dry_run`
    - `test_dry_run_property_returns_false_by_default`
    - `test_dry_run_property_is_read_only`

3. **Integration tests** (`tests/bake/cli/bake/test_bake_main.py`)
    - `test_dry_run_flag_false_by_default`
    - `test_dry_run_flag_with_long_flag`
    - `test_dry_run_flag_with_short_flag`

**Test Results:** All 692 tests pass, 94% coverage

### Bonus: Context Re-export ✅

**Also completed:** Made `Context` available for direct import from `bake` package.

**Changes:**

- `src/bake/__init__.py` now re-exports `Context` from `bake.cli.common.context`
- Updated all imports to use `from bake import Context` instead of `from bake.cli.common.context import Context`
- Fixed circular import issue in `version.py` by using `importlib.metadata` directly
- Used `typer.Context` (instead of `Context`) in `params.py` and `obj.py` to avoid circular imports

**Files Updated:**

- `src/bake/__init__.py` - Re-exports `Context`
- `src/bake/cli/utils/version.py` - Fixed circular import
- `src/bake/cli/bakefile/*.py` - Updated imports
- `src/bake/cli/common/app.py` - Updated imports
- `tests/bake/cli/common/*.py` - Updated imports

**User API:**

```python
from bake import Context

# In user bakefile commands
@bakebook.command()
def deploy(ctx: Context) -> None:
    if ctx.obj.dry_run:
        console.echo("[DRY RUN] Would deploy")
        return
    # Actual deployment
```

---

## What Was NOT Completed

### Phase 2: Framework Commands Dry Run (CANCELLED)

**Status:** See `phase2-framework-commands-plan.md` for details. This phase was planned but not implemented.

**Reason:** Deferred to future work. Core dry run infrastructure is complete for user commands. Framework commands (`init`, `add-inline`, `lint`, `uv sync`, etc.) would need additional work to respect the dry run flag.

### Phase 3: Documentation (NOT STARTED)

- CLI help text already shows `-n, --dry-run` option (via typer)
- User documentation not yet added to README or other docs

---

## Design Decisions

1. **Storage:** `dry_run` stored in `BakefileObject.dry_run` (single source of truth)
2. **Access:** `Context.dry_run` property provides user-friendly access
3. **CLI Convention:** `-n` short form (common convention: make, nix), `--dry-run` long form
4. **Scope:** Both `bake` and `bakefile` CLIs
5. **Behavior:** Flag controls execution, not output (separation from verbosity)

---

## Related Files

**Core Implementation:**

- `src/bake/cli/common/params.py` - dry_run_option definition
- `src/bake/cli/common/obj.py` - BakefileObject.dry_run field
- `src/bake/cli/common/context.py` - Context.dry_run property
- `src/bake/cli/common/app.py` - bake_app_callback parameter

**Context Re-export:**

- `src/bake/__init__.py` - Re-exports Context
- `src/bake/cli/utils/version.py` - Fixed circular import

**Tests:**

- `tests/bake/cli/common/test_obj.py` - Flag parsing tests
- `tests/bake/cli/common/test_context.py` - Property tests
- `tests/bake/cli/bake/test_bake_main.py` - Integration tests

---

## Verification Commands

```bash
make lint   # All checks pass
make test   # All 692 tests pass
```

---

## Future Work

1. **Framework Commands Dry Run** - See `phase2-framework-commands-plan.md`
2. **Helper Methods** - Add `ctx.run()` and `ctx.run_script()` methods that respect dry_run
3. **User Documentation** - Document dry run usage in README/user guide
