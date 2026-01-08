# Context: Bakefile Dependency Management Commands

**Last Updated:** 2026-01-03
**Status:** IN PROGRESS (Commands 1-4: pip, add, lock, sync ✅ COMPLETE)

---

## SESSION PROGRESS

### ✅ COMPLETED

- Dev docs plan created with comprehensive implementation strategy
- Technical decisions documented (pass-through pattern)
- Code patterns and error handling defined
- **Command 1: pip** - FULLY IMPLEMENTED AND TESTED
- **Command 2: add** - FULLY IMPLEMENTED AND TESTED
- **Command 3: lock** - FULLY IMPLEMENTED AND TESTED
- **Command 4: sync** - FULLY IMPLEMENTED AND TESTED

### 🟡 IN PROGRESS

- Ready to start Phase 3: Testing & Documentation (unit tests and CLI tests for sync)

### ⏳ NEXT STEPS

1. Write unit tests for `run_uv_sync` function
2. Write CLI tests for `bakefile sync` command
3. Update documentation (README.md, CLAUDE.md if needed)

### ⚠️ BLOCKERS

- None

---

## IMPLEMENTATION NOTES - Command 1: pip

### Actual Implementation vs Plan

The plan specified `src/bake/manage/pip.py` but the actual implementation uses `src/bake/manage/run_uv_pip.py`.

### Files Created/Modified for pip Command

1. **`src/bake/manage/run_uv_pip.py`** - Core logic module
    - Function: `run_uv_pip(bakefile_path: Path | None, cmd: list[str])`
    - Handles both inline and project-level bakefiles
    - Shows warning when no PEP 723 metadata found
    - Displays Python version being used
    - Uses `run_uv()` with tuple args: `("pip", *cmd, "--python", str(python_path))`

2. **`src/bake/cli/bakefile/pip.py`** - CLI command
    - Uses `Literal` type for pip subcommands (compile, sync, install, etc.)
    - First arg is the pip subcommand (required)
    - Remaining args captured via `typer_ctx.args`
    - Passes `cmd = [command, *typer_ctx.args]` to `run_uv_pip()`

3. **`src/bake/cli/bakefile/main.py`** - Command registration
    - Import: `from .pip import pip`
    - Registration with context settings for extra args:
        ```python
        bakefile_app.command(
            context_settings={
                "allow_extra_args": True,
                "ignore_unknown_options": True,
            }
        )(pip)
        ```

### Key Implementation Details

1. **run_uv() call pattern**: Uses tuple `(pip, *cmd, --python, path)` NOT individual args
2. **Python version display**: Shows version before running pip command
3. **Error handling**: Catches `PythonNotFoundError` and `BakebookError`
4. **Warning for project-level**: Advises using `uv pip` directly when no inline metadata

### Deviation from Original Plan

| Aspect             | Plan                                     | Actual                                            |
| ------------------ | ---------------------------------------- | ------------------------------------------------- |
| Manage module name | `pip.py`                                 | `run_uv_pip.py`                                   |
| Function signature | `run_pip(python_path: Path, *args: str)` | `run_uv_pip(bakefile_path: Path, cmd: list[str])` |
| run_uv() args      | Individual string args                   | Tuple of args                                     |
| CLI arg capture    | `args: list[str] = typer.Argument(...)`  | Typed command + `typer_ctx.args`                  |

The actual implementation is better as it:

- Provides subcommand type safety via `Literal`
- Shows Python version to user
- Gives helpful warning for project-level usage

---

## IMPLEMENTATION NOTES - Command 2: add ✅ COMPLETE

### Files Created for add Command

1. **`src/bake/manage/run_uv_add.py`** - Core logic module
    - Function: `run_uv_add(bakefile_path: Path | None, cmd: list[str])`
    - REQUIRES PEP 723 inline metadata (no fallback to project-level)
    - Uses `run_uv()` with tuple args: `("add", "--script", bakefile_path.name, *cmd)`
    - Runs in `bakefile_path.parent` directory
    - Shows success message after adding dependencies
    - Reuses `_has_inline_metadata()` from `find_python.py`

2. **`src/bake/cli/bakefile/add.py`** - CLI command
    - Uses `typer_ctx.args` to capture all args
    - Calls `run_uv_add(bakefile_path, args)`
    - Error handling for `BakebookError` and `PythonNotFoundError`

3. **`tests/bake/manage/test_run_uv_add.py`** - Unit tests (3 tests, 100% coverage)
4. **`tests/bake/cli/bakefile/test_bakefile_add.py`** - CLI tests (3 tests)

5. **`src/bake/cli/bakefile/main.py`** - Command registration
    - Import: `from . import add`
    - Registration with context settings for extra args

### Key Implementation Details

1. **Validation**: Raises `BakebookError` if no inline metadata (no warning, hard fail)
2. **Error message**: Suggests `bakefile add-inline` or using `uv add` directly
3. **run_uv() call**: Uses tuple pattern with `cwd=bakefile_path.parent`
4. **Success message**: `console.success(f"Dependencies added to {bakefile_path.name}")`

---

## Key Files

### Existing Code to Reference

| File                                   | Purpose                                          |
| -------------------------------------- | ------------------------------------------------ |
| `src/bake/manage/find_python.py`       | Python detection logic, `_has_inline_metadata()` |
| `src/bake/cli/bakefile/find_python.py` | CLI command pattern                              |
| `src/bake/cli/bakefile/main.py`        | Command registration                             |
| `src/bake/ui/run/run.py`               | `run_uv()` wrapper function                      |
| `src/bake/cli/bakefile/add_inline.py`  | Error handling pattern                           |

### Files to Create

| File                            | Status  | Purpose                       |
| ------------------------------- | ------- | ----------------------------- |
| `src/bake/manage/run_uv_pip.py` | ✅ DONE | uv pip pass-through           |
| `src/bake/manage/run_uv.py`     | ✅ DONE | uv add/lock/sync pass-through |
| `src/bake/cli/bakefile/pip.py`  | ✅ DONE | CLI command                   |
| `src/bake/cli/bakefile/add.py`  | ✅ DONE | CLI command                   |
| `src/bake/cli/bakefile/lock.py` | ✅ DONE | CLI command                   |
| `src/bake/cli/bakefile/sync.py` | ✅ DONE | CLI command                   |

---

## IMPLEMENTATION NOTES - Command 4: sync ✅ COMPLETE

### Files Created for sync Command

1. **`src/bake/manage/run_uv.py`** - Added `run_uv_sync` function
    - Function: `run_uv_sync(bakefile_path: Path | None, cmd: list[str])`
    - REQUIRES PEP 723 inline metadata (no fallback to project-level)
    - Uses shared `_run_uv()` helper with `command_name="sync"`
    - Uses `run_uv()` with tuple args: `("sync", "--script", bakefile_path.name, *cmd)`
    - Runs in `bakefile_path.parent` directory
    - Reuses `_has_inline_metadata()` from `find_python.py`

2. **`src/bake/cli/bakefile/sync.py`** - CLI command
    - Uses `typer_ctx.args` to capture all args
    - Calls `run_uv_sync(bakefile_path, args)`
    - Error handling for `BakebookError` and `PythonNotFoundError`

3. **`src/bake/cli/bakefile/main.py`** - Command registration
    - Import: `from . import sync`
    - Registration with context settings for extra args

### Key Implementation Details

1. **Validation**: Raises `BakebookError` if no inline metadata (via shared `_run_uv`)
2. **Error message**: Suggests `bakefile add-inline` or using `uv sync` directly
3. **run_uv() call**: Uses tuple pattern with `cwd=bakefile_path.parent`
4. **Consistency**: Follows exact same pattern as add/lock commands

---

## Key Design Decisions

### 1. Pass-Through Pattern (No Option Parsing)

- `bakefile` commands don't parse options - just pass through to uv
- User gets full uv capability automatically
- When uv adds new options, they just work
- Trade-off: No typer help/validation for uv options (but uv has its own help)

### 2. Command Scope

| Command         | Works On              | Validation                    |
| --------------- | --------------------- | ----------------------------- |
| `pip`           | Both inline & project | None - let uv handle          |
| `add/lock/sync` | Inline metadata only  | Must have PEP 723, else error |

**Rationale:**

- `add/lock/sync` with `--script` is specifically for PEP 723 bakefiles
- Project-level dependency management should use `uv` directly
- Clearer mental model

### 3. run_uv() Usage Pattern

`run_uv()` takes individual string arguments:

```python
run_uv("pip", "install", "requests", "--python", str(python_path))
```

NOT: `run_uv("pip", f"--python {python_path}")`

---

## Code Patterns (Ready for Implementation)

### Manage Module Pattern

```python
# src/bake/manage/pip.py
import logging
from pathlib import Path

from bake.ui.run import run_uv

logger = logging.getLogger(__name__)

def run_pip(python_path: Path, *args: str) -> None:
    """Run uv pip command with Python path."""
    logger.debug(f"Running uv pip with args: {args}")
    run_uv("pip", *args, "--python", str(python_path))
```

```python
# src/bake/manage/add.py
import logging
from pathlib import Path

from bake.manage.add_inline import read_inline
from bake.utils.exceptions import BakebookError
from bake.ui.run import run_uv

logger = logging.getLogger(__name__)

def _has_inline_metadata(bakefile_path: Path) -> bool:
    """Check if bakefile has PEP 723 inline metadata."""
    inline_metadata = read_inline(bakefile_path)
    return inline_metadata is not None

def add_dependencies(bakefile_path: Path, *args: str) -> None:
    """Add dependencies to bakefile (requires PEP 723 metadata)."""
    if not _has_inline_metadata(bakefile_path):
        raise BakebookError(
            f"{bakefile_path.name} requires PEP 723 inline metadata. "
            f"Run 'bakefile add-inline' to add metadata, "
            f"or use 'uv add' for project-level dependencies."
        )
    logger.debug(f"Adding dependencies to {bakefile_path}")
    run_uv("add", "--script", bakefile_path.name, *args,
           cwd=bakefile_path.parent)
```

### CLI Command Pattern

```python
# src/bake/cli/bakefile/pip.py
import typer

from bake.cli.common.context import Context
from bake.manage.find_python import find_python as find_python_path
from bake.manage.pip import run_pip

def pip(
    ctx: Context,
    args: list[str] = typer.Argument(...),
) -> None:
    """Run uv pip commands with bakefile's Python."""
    python_path = find_python_path(ctx.obj.bakefile_path)
    run_pip(python_path, *args)
```

```python
# src/bake/cli/bakefile/add.py
import typer

from bake.cli.common.context import Context
from bake.manage.add import add_dependencies
from bake.ui import console
from bake.utils.exceptions import BakebookError

def add(
    ctx: Context,
    args: list[str] = typer.Argument(...),
) -> None:
    """Add dependencies to bakefile (requires PEP 723 metadata)."""
    try:
        add_dependencies(ctx.obj.bakefile_path, *args)
        console.success(f"Dependencies added to {ctx.obj.bakefile_path.name}")
    except BakebookError as e:
        console.error(str(e))
        raise typer.Exit(1) from None
```

---

## UV Command Reference

### bakefile pip → uv pip

```bash
# bakefile injects --python, user provides rest
uv pip install requests --python /path/to/python
```

### bakefile add → uv add

```bash
# bakefile injects --script, user provides packages
uv add --script bakefile.py requests
```

### bakefile lock → uv lock

```bash
uv lock --script bakefile.py
```

### bakefile sync → uv sync

```bash
uv sync --script bakefile.py
```

---

## Important Notes

1. **`run_uv()` signature**: Takes `*args: str`, each as separate argument
2. **`--python` position**: Can go anywhere in args, uv handles it
3. **`--script` position**: Must come before packages in uv add
4. **`cwd` parameter**: Required for `add/lock/sync` to work with `--script`

---

## Error Message Pattern

When inline metadata is missing:

```python
raise BakebookError(
    f"{bakefile_path.name} requires PEP 723 inline metadata. "
    f"Run 'bakefile add-inline' to add metadata, "
    f"or use 'uv add' for project-level dependencies."
)
```

---

## Dependencies

- Python 3.14+
- uv (CLI tool)
- typer (CLI framework)
- Existing `find_python()` function
- Existing `run_uv()` wrapper (now in `bake.ui.run`)
- Existing `read_inline()` from `bake.manage.add_inline`
