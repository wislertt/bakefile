# Dry Run Flag - Task Checklist

## Phase 1: Core Infrastructure ✅ COMPLETED

### 1.1 Add dry_run_option to params.py

- [x] Define `dry_run_option` Annotated type with `-n` and `--dry-run`
- [x] Add clear help text
- [x] Run `make lint` to verify no errors

**File:** `src/bake/cli/common/params.py`

---

### 1.2 Add dry_run to BakefileObject

- [x] Add `dry_run: bool = False` field to dataclass
- [x] Verify default value is `False`
- [x] Run `make lint` to verify no errors

**File:** `src/bake/cli/common/obj.py`

---

### 1.3 Add dry_run to \_get_bakefile_object

- [x] Add `dry_run: dry_run_option = False` parameter
- [x] Pass `dry_run=dry_run` to BakefileObject constructor
- [x] Run `make lint` to verify no errors

**File:** `src/bake/cli/common/obj.py`

---

### 1.4 Add dry_run property to Context

- [x] Define `@property def dry_run(self) -> bool:`
- [x] Return `self.obj.dry_run`
- [x] Run `make lint` to verify no errors

**File:** `src/bake/cli/common/context.py`

---

### 1.5 Add \_dry_run to bake_app_callback

- [x] Add `_dry_run: dry_run_option = False` parameter
- [x] Import `dry_run_option` from params
- [x] Run `make lint` to verify no errors

**File:** `src/bake/cli/common/app.py`

---

### 1.6 Update imports

- [x] Add `dry_run_option` to imports in `app.py`
- [x] Verify no circular import errors
- [x] Run `make lint` to verify no errors

**Files:** `src/bake/cli/common/app.py`, `src/bake/cli/common/obj.py`

---

## Phase 2: Testing ✅ COMPLETED

### 2.1 Test dry_run flag parsing

- [x] Test default value is `False`
- [x] Test `--dry-run` sets to `True`
- [x] Test `-n` sets to `True`
- [x] Test works with both `bake` and `bakefile` CLIs
- [x] Run `make test` to verify all pass

**File:** `tests/bake/cli/common/test_obj.py`

**Tests Added:**

- `test_get_bakefile_object_dry_run_default_is_false`
- `test_get_bakefile_object_dry_run_with_long_flag`
- `test_get_bakefile_object_dry_run_with_short_flag`

---

### 2.2 Test ctx.dry_run property

- [x] Test `ctx.dry_run` returns correct value
- [x] Test `ctx.dry_run` == `ctx.obj.dry_run`
- [x] Test property is read-only (cannot assign)
- [x] Run `make test` to verify all pass

**File:** `tests/bake/cli/common/test_context.py`

**Tests Added:**

- `test_dry_run_property_returns_obj_dry_run`
- `test_dry_run_property_returns_false_by_default`
- `test_dry_run_property_is_read_only`

---

### 2.3 Integration test with example bakefile

- [x] Create test bakefile with command checking `ctx.obj.dry_run`
- [x] Test without flag (dry_run is False)
- [x] Test with `-n` flag (dry_run is True)
- [x] Test with `--dry-run` flag (dry_run is True)
- [x] Run `make test` to verify all pass

**File:** `tests/bake/cli/bake/test_bake_main.py`

**Tests Added:**

- `TestDryRunIntegration.test_dry_run_flag_false_by_default`
- `TestDryRunIntegration.test_dry_run_flag_with_long_flag`
- `TestDryRunIntegration.test_dry_run_flag_with_short_flag`

---

## Phase 3: Documentation (FUTURE) ⏳ NOT STARTED

### 3.1 Update CLI help text

- [ ] Verify help shows `-n, --dry-run` option
- [ ] Verify help text is clear

---

### 3.2 Add user documentation

- [ ] Document how to use `ctx.dry_run` in bakefiles
- [ ] Provide examples
- [ ] Document behavior for bakefile CLI commands

---

## Phase 4: Framework Commands Dry Run (NEXT) ⏳ NOT STARTED

**Plan:** See `phase2-framework-commands-plan.md`

**Overview:** Add dry_run support to all `bakefile` CLI commands (`init`, `add-inline`, `lint`, `uv sync`, `uv lock`, `uv add`, `uv pip`).

**Pattern:** Pass `dry_run` flag down through the call chain to `run()` function

```python
# CLI command
def sync(typer_ctx: typer.Context, ...) -> None:
    result = run_uv_sync(bakefile_path, args, dry_run=typer_ctx.obj.dry_run)

# Manage function
def run_uv_sync(bakefile_path, cmd, dry_run=False):
    return run_uv(("sync", ...), dry_run=dry_run, ...)

# Run function
def run_uv(cmd, dry_run=False, **kwargs):
    if dry_run:
        console.echo(f"[DRY RUN] Would run: uv {' '.join(cmd)}")
        return CompletedProcess(returncode=0)
    return run(("uv", *cmd), **kwargs)
```

**Phases:**

1. **Core Infrastructure** - Update `run()`, `run_uv()` functions
2. **Manage Functions** - Add `dry_run` parameter to all manage functions
3. **CLI Commands** - Pass `ctx.obj.dry_run` to manage functions

---

## Quick Resume

**Current Status:** Phase 2 complete, feature ready for use

**Completed:**

- Phase 1: Core Infrastructure
    - Added `dry_run_option` to params.py (src/bake/cli/common/params.py:64-67)
    - Added `dry_run` field to BakefileObject (src/bake/cli/common/obj.py:49)
    - Added `dry_run` parameter to `_get_bakefile_object` (src/bake/cli/common/obj.py:130)
    - Added `dry_run` property to Context (src/bake/cli/common/context.py:9-11)
    - Added `_dry_run` parameter to `bake_app_callback` (src/bake/cli/common/app.py:43)
    - Updated imports in app.py and obj.py
    - All linters pass (make lint)

- Phase 2: Testing
    - Added 3 tests for dry_run flag parsing (test_obj.py)
    - Added 3 tests for ctx.dry_run property (test_context.py)
    - Added 3 integration tests (test_bake_main.py)
    - All 696 tests pass (make test)
    - Coverage: 95%

**Next Steps:**

- Phase 3: Documentation (future)
- Phase 4: Framework Commands Dry Run (see phase2-framework-commands-plan.md)

**User API:**

Users can access `dry_run` via `ctx.obj.dry_run` in their bakefile commands:

```python
import typer
from bake.ui import console

bakebook = typer.Typer()

@bakebook.command()
def deploy(ctx: typer.Context):
    if ctx.obj.dry_run:
        console.echo("[DRY RUN] Would deploy to production")
        return
    # Actual deployment
```

**Verification Commands:**

```bash
make lint   # Check code quality
make test   # Run tests
```

## Last Updated: 2025-01-04
