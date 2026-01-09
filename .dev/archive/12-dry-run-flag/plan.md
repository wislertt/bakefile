# Dry Run Flag - Implementation Plan

## Executive Summary

Add a `--dry-run` / `-n` flag to both `bake` and `bakefile` CLIs. This flag allows users to preview what would happen without executing commands.

**Scope:** Both `bake` CLI (user tasks) and `bakefile` CLI (framework commands)

**User Access:** `ctx.dry_run` (property that reads from `ctx.obj.dry_run`)

**Behavior:** Skip execution, respect echo settings (output controlled by verbosity, not dry run itself)

---

## Current State Analysis

### Existing Architecture

**BakefileObject** (`bake/cli/common/obj.py`):

- Dataclass holding CLI state: `chdir`, `file_name`, `bakebook_name`, `bakefile_path`, `bakebook`, `verbosity`
- Created by `get_bakefile_object()` → `_get_bakefile_object` hidden command
- Passed to context via `bake_app_callback_with_obj()`

**Two Entry Points:**

- `bake` CLI (`bake/cli/bake/main.py`) - Runs user tasks from bakefile.py
- `bakefile` CLI (`bake/cli/bakefile/main.py`) - Manages bakefile projects

**Parameter Flow:**

```
get_bakefile_object()
  → _get_bakefile_object (hidden typer command)
  → Parses args, creates BakefileObject
  → Returns BakefileObject

bake_app_callback_with_obj(obj)
  → Creates callback function
  → callback sets ctx.obj = BakefileObject

User commands access via:
  - ctx.obj.verbosity
  - ctx.obj.chdir
  - etc.
```

### Design Decision: Why Not Just Another obj Parameter?

**Semantic Difference:**

| Parameter       | Category           | User Access                                      |
| --------------- | ------------------ | ------------------------------------------------ |
| `dry_run`       | **User-facing**    | `if ctx.dry_run:` - Frequently used in user code |
| `verbosity`     | Framework-internal | Used by logging setup                            |
| `chdir`         | Framework-internal | Used by bakefile resolution                      |
| `file_name`     | Framework-internal | Used by bakefile resolution                      |
| `bakebook_name` | Framework-internal | Used by bakebook retrieval                       |

**`dry_run` is different:**

- User-facing execution mode, not just configuration
- Frequently accessed in user code
- Will be used by `ctx.run()` and `ctx.run_script()` methods
- Deserves direct access via `ctx.dry_run`, not `ctx.obj.dry_run`

---

## Proposed Future State

### User API

```python
# In user's bakefile.py
import typer
from bake.ui import console

bakebook = typer.Typer()

@bakebook.command()
def deploy(ctx: typer.Context) -> None:
    if ctx.dry_run:
        console.echo("[DRY RUN] Would deploy to production")
        return

    # Actual deployment
    console.success("Deploying...")
```

Or using helper methods (future):

```python
@bakebook.command()
def deploy(ctx: typer.Context) -> None:
    # ctx.run() respects dry_run automatically
    ctx.run("kubectl apply -f deployment.yaml")
```

### CLI Usage

```bash
# Dry run for bake commands
bake -n hello
bake --dry-run build --prod

# Dry run for bakefile commands
bakefile -n lint
bakefile --dry-run uv sync

# Combined with verbosity
bake -n -vv build  # Verbose dry run
```

### Implementation Design

**Single Source of Truth:**

- `dry_run` stored in `BakefileObject.dry_run`
- `Context.dry_run` is a `@property` that returns `self.obj.dry_run`

```python
# BakefileObject - stores the value
@dataclass
class BakefileObject:
    ...
    dry_run: bool = False

# Context - provides user-friendly access
class Context(typer.Context):
    obj: BakefileObject

    @property
    def dry_run(self) -> bool:
        return self.obj.dry_run
```

---

## Implementation Phases

### Phase 1: Core Infrastructure (Files Modified)

**Objective:** Add the dry run flag to the parameter parsing system

| File                         | Change                                                       |
| ---------------------------- | ------------------------------------------------------------ |
| `bake/cli/common/params.py`  | Add `dry_run_option` Annotated type                          |
| `bake/cli/common/obj.py`     | Add `dry_run` to `BakefileObject` and `_get_bakefile_object` |
| `bake/cli/common/context.py` | Add `@property def dry_run` to `Context`                     |
| `bake/cli/common/app.py`     | Add `_dry_run` param to `bake_app_callback`                  |

### Phase 2: Framework Command Integration (Future Work)

**Objective:** Make `bakefile` commands respect dry run

Commands to update:

- `uv sync` - Skip package installation
- `uv lock` - Skip lock file update
- `uv add` - Skip package addition
- `uv pip` - Skip pip operations
- `init` - Skip file creation
- `add-inline` - Skip code injection

### Phase 3: Helper Methods (Future Work)

**Objective:** Add convenience methods to Context

```python
class Context(typer.Context):
    def run(self, cmd: str) -> None:
        run(cmd, dry_run=self.dry_run)

    def run_script(self, script: str) -> None:
        run_script(script, dry_run=self.dry_run)
```

---

## Detailed Tasks

### Phase 1: Core Infrastructure

#### Task 1.1: Add dry_run_option to params.py

**File:** `src/bake/cli/common/params.py`

**Change:**

```python
dry_run_option = Annotated[
    bool,
    typer.Option(
        "-n", "--dry-run",
        help="Dry run (show what would be done without executing)"
    ),
]
```

**Acceptance:**

- Option defined with `-n` short flag and `--dry-run` long flag
- Help text is clear
- No lint/type errors

**Effort:** S (Small)

---

#### Task 1.2: Add dry_run to BakefileObject

**File:** `src/bake/cli/common/obj.py`

**Change:**

```python
@dataclass
class BakefileObject:
    chdir: Path
    file_name: str
    bakebook_name: str
    bakefile_path: Path | None = None
    bakebook: BakebookType | None = None
    verbosity: int = 0
    dry_run: bool = False  # NEW
```

**Acceptance:**

- Field added to dataclass
- Default value is `False`
- No lint/type errors

**Effort:** S (Small)

---

#### Task 1.3: Add dry_run to \_get_bakefile_object

**File:** `src/bake/cli/common/obj.py`

**Change:**

```python
@bakefile_obj_app.command(...)
def _get_bakefile_object(
    ctx: typer.Context,
    chdir: chdir_option = DEFAULT_CHDIR,
    file_name: file_name_option = DEFAULT_FILE_NAME,
    bakebook_name: bakebook_name_option = DEFAULT_BAKEBOOK_NAME,
    is_chain_commands: is_chain_commands_option = None,
    remaining_args: remaining_args_argument = None,
    verbosity: verbosity_option = 0,
    dry_run: dry_run_option = False,  # NEW
):
    ...
    return BakefileObject(
        chdir=chdir,
        file_name=file_name,
        bakebook_name=bakebook_name,
        verbosity=verbosity,
        dry_run=dry_run,  # NEW
    )
```

**Acceptance:**

- Parameter added to function signature
- Value passed to BakefileObject constructor
- No lint/type errors

**Effort:** S (Small)

---

#### Task 1.4: Add dry_run property to Context

**File:** `src/bake/cli/common/context.py`

**Change:**

```python
from .obj import BakefileObject

class Context(typer.Context):
    obj: BakefileObject

    @property
    def dry_run(self) -> bool:
        return self.obj.dry_run
```

**Acceptance:**

- Property defined with correct type hint
- Returns `self.obj.dry_run`
- No lint/type errors

**Effort:** S (Small)

---

#### Task 1.5: Add \_dry_run to bake_app_callback

**File:** `src/bake/cli/common/app.py`

**Change:**

```python
def bake_app_callback(
    ctx: Context,
    _chdir: chdir_option = DEFAULT_CHDIR,
    _file_name: file_name_option = DEFAULT_FILE_NAME,
    _bakebook_name: bakebook_name_option = DEFAULT_BAKEBOOK_NAME,
    _version: version_option = False,
    _is_chain_commands: is_chain_commands_option = None,
    _verbosity: verbosity_option = 0,
    _dry_run: dry_run_option = False,  # NEW
):
    ctx.obj = obj
    # Note: obj.dry_run is already set by get_bakefile_object()
    show_help_if_no_command(ctx)
```

**Acceptance:**

- Parameter added to callback signature
- Parameter is prefixed with `_` (internal use, not reassigned)
- No lint/type errors
- Callback doesn't crash

**Note:** The `_dry_run` parameter is necessary for Typer to parse the flag, but we don't need to do anything with it because `get_bakefile_object()` already parses it and sets `obj.dry_run`.

**Effort:** S (Small)

---

#### Task 1.6: Update imports

**Files:** `bake/cli/common/app.py`, `bake/cli/common/obj.py`

**Change:** Add `dry_run_option` to imports from `params.py`

```python
from bake.cli.common.params import (
    bakebook_name_option,
    chdir_option,
    dry_run_option,  # NEW
    file_name_option,
    ...
)
```

**Acceptance:**

- Import added
- No circular import errors
- No lint errors

**Effort:** S (Small)

---

### Phase 2: Testing

#### Task 2.1: Test dry_run flag parsing

**File:** New test file or update existing `tests/bake/cli/common/test_obj.py`

**Tests:**

- Default is `False`
- `--dry-run` sets to `True`
- `-n` sets to `True`
- Works with both `bake` and `bakefile` CLIs

**Acceptance:**

- All tests pass
- Coverage for dry_run option

**Effort:** M (Medium)

---

#### Task 2.2: Test ctx.dry_run access

**File:** New test file

**Tests:**

- `ctx.dry_run` returns correct value
- `ctx.dry_run` == `ctx.obj.dry_run`
- Property is read-only

**Acceptance:**

- All tests pass
- Property behavior verified

**Effort:** S (Small)

---

#### Task 2.3: Integration test with example bakefile

**File:** New test file or update existing

**Test:**

- Create a bakefile with a command that checks `ctx.dry_run`
- Run with `-n` flag
- Verify dry run behavior

**Acceptance:**

- Test passes
- User can access `ctx.dry_run` in their bakefile

**Effort:** M (Medium)

---

### Phase 3: Documentation (Future)

#### Task 3.1: Update CLI help text

- Ensure help shows `-n, --dry-run` option
- Help text is clear

#### Task 3.2: Add user documentation

- Document how to use `ctx.dry_run` in bakefiles
- Provide examples

---

## Risk Assessment

| Risk                              | Probability | Impact | Mitigation                                    |
| --------------------------------- | ----------- | ------ | --------------------------------------------- |
| Breaking existing CLI behavior    | Low         | High   | Add as optional flag, default `False`         |
| Typer callback parameter mismatch | Low         | Medium | Ensure all callbacks use same parameter types |
| Property access confusion         | Low         | Low    | Clear documentation, property is simple       |
| Circular import issues            | Low         | Medium | Careful import order, test imports            |

---

## Success Metrics

1. **Functional:**
    - `--dry-run` / `-n` flag works on both `bake` and `bakefile` CLIs
    - `ctx.dry_run` accessible in user bakefile commands
    - No breaking changes to existing functionality

2. **Code Quality:**
    - All tests pass (`make test`)
    - No lint errors (`make lint`)
    - Type hints correct

3. **User Experience:**
    - Flag follows common CLI conventions (`-n` short form)
    - Clear help text
    - Intuitive API (`ctx.dry_run` not `ctx.obj.dry_run`)

---

## Timeline Estimates

| Phase                        | Estimated Time         |
| ---------------------------- | ---------------------- |
| Phase 1: Core Infrastructure | 30-45 minutes          |
| Phase 2: Testing             | 30-45 minutes          |
| Phase 3: Documentation       | 15-30 minutes (future) |
| **Total**                    | **1.5-2 hours**        |

---

## Dependencies

- None - standalone feature
- Can be implemented independently

---

## Last Updated: 2025-01-04
