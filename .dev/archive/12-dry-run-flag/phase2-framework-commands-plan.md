# Framework Commands Dry Run Support - Plan

## Executive Summary

Add dry_run support to all `bakefile` CLI commands. When `--dry-run` / `-n` is passed, commands should:

1. **Skip execution** - Don't create/modify files or run external commands
2. **Show what would be done** - Print clear messages about intended actions
3. **Return success** - Exit code 0 (unless there's a validation error)

---

## Current State Analysis

### Existing Commands

| Command      | File            | Side Effects           | Current Behavior                  |
| ------------ | --------------- | ---------------------- | --------------------------------- |
| `init`       | `init.py`       | Creates `bakefile.py`  | Writes file, adds inline metadata |
| `add-inline` | `add_inline.py` | Modifies `bakefile.py` | Adds PEP 723 metadata             |
| `lint`       | `lint.py`       | Runs linters           | Executes ruff/ty commands         |
| `uv sync`    | `uv.py`         | Runs `uv sync`         | Installs packages                 |
| `uv lock`    | `uv.py`         | Runs `uv lock`         | Updates lock file                 |
| `uv add`     | `uv.py`         | Runs `uv add`          | Adds dependencies                 |
| `uv pip`     | `uv.py`         | Runs `uv pip`          | Pip operations                    |

### Key Functions Called

| Function                | File                       | Purpose               |
| ----------------------- | -------------------------- | --------------------- |
| `write_bakefile()`      | `manage/write_bakefile.py` | Creates bakefile.py   |
| `add_inline_metadata()` | `manage/add_inline.py`     | Adds PEP 723 metadata |
| `run_ruff_format()`     | `manage/lint.py`           | Runs ruff format      |
| `run_ruff_check()`      | `manage/lint.py`           | Runs ruff check       |
| `run_ty_check()`        | `manage/lint.py`           | Runs type checking    |
| `run_uv_sync()`         | `manage/run_uv.py`         | Runs uv sync          |
| `run_uv_lock()`         | `manage/run_uv.py`         | Runs uv lock          |
| `run_uv_add()`          | `manage/run_uv.py`         | Runs uv add           |
| `run_uv_pip()`          | `manage/run_uv.py`         | Runs uv pip           |

---

## Design Decisions

### 1. Dry Run Pattern: Pass Through to `run()`

**Approach:** Pass `ctx.obj.dry_run` down through the call chain until it reaches `run()` or file operation functions.

**IMPORTANT:** The `dry_run` parameter in manage functions is **required** (no default value). This ensures all callers explicitly pass the value.

**Pattern for CLI commands:**

```python
from bake.cli.common.context import Context

def sync(ctx: Context, ...) -> None:
    """Sync dependencies using uv."""
    bakefile_path = ctx.obj.bakefile_path
    args = list(ctx.args)

    if upgrade:
        args.append("--upgrade")
    if reinstall:
        args.append("--reinstall")

    # Pass dry_run down to manage function
    try:
        result = run_uv_sync(bakefile_path=bakefile_path, cmd=args, dry_run=ctx.obj.dry_run)
        raise typer.Exit(result.returncode)
    except (PythonNotFoundError, BakebookError) as e:
        console.error(str(e))
        raise typer.Exit(code=1) from None
```

**Pattern for manage functions:**

```python
def run_uv_sync(
    bakefile_path: Path | None, cmd: list[str], dry_run: bool
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[None]:
    """Run uv sync command."""
    if bakefile_path is None or not bakefile_path.exists():
        raise PythonNotFoundError(f"Bakefile not found at {bakefile_path}")

    if not _has_inline_metadata(bakefile_path):
        error_msg = (
            f"`sync` command requires PEP 723 inline metadata in the bakefile. "
            f"Run {style.code('bakefile add-inline')} to add metadata."
        )
        raise BakebookError(error_msg)

    # Pass dry_run down to run_uv
    return run_uv(
        ("sync", "--script", bakefile_path.name, *cmd),
        dry_run=dry_run,
        capture_output=True,
        stream=True,
        check=True,
        echo=True,
        cwd=bakefile_path.parent,
    )
```

**Pattern for run/run_uv:**

> **Note:** These functions already support `dry_run` parameter. No changes needed.

```python
def run_uv(cmd: tuple[str, ...], dry_run: bool = False, **kwargs) -> subprocess.CompletedProcess:
    """Run a uv command, optionally in dry run mode."""
    uv_bin = find_uv_bin()
    display_cmd = "uv " + " ".join(cmd)

    if echo:
        console.cmd(display_cmd)

    # Call run with full uv binary path, echo=False (already displayed), pass through dry_run
    return run(
        [uv_bin, *cmd],
        capture_output=capture_output,
        check=check,
        cwd=cwd,
        stream=stream,
        echo=False,
        dry_run=dry_run,  # <-- This is where dry_run is handled
        **kwargs,
    )
```

**For file operations:**

```python
def write_bakefile(..., dry_run: bool):
    if dry_run:
        console.echo(f"[DRY RUN] Would write bakefile to {bakefile_path}")
        return

    # Actual write
    bakefile_path.write_text(content)
```

**Rationale:**

- Single source of truth for dry_run handling (in `run()` function)
- No code duplication across CLI commands
- Clean separation of concerns
- File operations can handle their own dry_run messaging appropriately
- Commands stay focused on orchestration, not presentation
- Required parameter ensures all callers explicitly pass the value

### 2. Parameter Flow

```
CLI Command (ctx: Context)
    ↓ ctx.obj.dry_run (from BakefileObject)
Manage Function (run_uv_sync, write_bakefile, etc.)
    ↓ dry_run: bool (required parameter)
Run Function (run, run_uv)
    ↓ handles actual execution (prints "[DRY RUN]" and returns early)
```

**Key Points:**

- CLI commands use `ctx: Context` (from `bake.cli.common.context`)
- Access via `ctx.obj.dry_run` (not `ctx.dry_run` - runtime context is `click.core.Context`)
- Manage functions require `dry_run: bool` (no default)
- Test calls must explicitly pass `dry_run=False`

### 3. UV Commands - Complete Implementation Pattern

Here's the complete pattern for all UV commands:

```python
# src/bake/cli/bakefile/uv.py
from bake.cli.common.context import Context
from bake.manage.run_uv import run_uv_add, run_uv_lock, run_uv_pip, run_uv_sync

def add(ctx: Context) -> None:
    """Add dependencies to bakefile."""
    bakefile_path = ctx.obj.bakefile_path
    args = ctx.args  # Not list() for add

    try:
        result = run_uv_add(bakefile_path=bakefile_path, cmd=args, dry_run=ctx.obj.dry_run)
        raise typer.Exit(result.returncode)
    except (PythonNotFoundError, BakebookError) as e:
        console.error(str(e))
        raise typer.Exit(code=1) from None

def lock(ctx: Context, upgrade: bool = False) -> None:
    """Lock dependencies."""
    bakefile_path = ctx.obj.bakefile_path
    args = list(ctx.args)  # list() for lock

    if upgrade:
        args.append("--upgrade")

    try:
        result = run_uv_lock(bakefile_path=bakefile_path, cmd=args, dry_run=ctx.obj.dry_run)
        raise typer.Exit(result.returncode)
    except (PythonNotFoundError, BakebookError) as e:
        console.error(str(e))
        raise typer.Exit(code=1) from None

def sync(ctx: Context, upgrade: bool = False, reinstall: bool = False) -> None:
    """Sync dependencies."""
    bakefile_path = ctx.obj.bakefile_path
    args = list(ctx.args)  # list() for sync

    if upgrade:
        args.append("--upgrade")
    if reinstall:
        args.append("--reinstall")

    try:
        result = run_uv_sync(bakefile_path=bakefile_path, cmd=args, dry_run=ctx.obj.dry_run)
        raise typer.Exit(result.returncode)
    except (PythonNotFoundError, BakebookError) as e:
        console.error(str(e))
        raise typer.Exit(code=1) from None

def pip(ctx: Context, command: PipCommand) -> None:
    """Run uv pip commands."""
    bakefile_path = ctx.obj.bakefile_path

    try:
        cmd = [command, *ctx.args]
        result = run_uv_pip(bakefile_path=bakefile_path, cmd=cmd, dry_run=ctx.obj.dry_run)
        raise typer.Exit(result.returncode)
    except (PythonNotFoundError, BakebookError) as e:
        console.error(str(e))
        raise typer.Exit(code=1) from None
```

**src/bake/manage/run_uv.py:**

```python
def run_uv_add(
    bakefile_path: Path | None, cmd: list[str], dry_run: bool
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[None]:
    return _run_uv(bakefile_path=bakefile_path, command_name="add", cmd=cmd, dry_run=dry_run)

def run_uv_lock(
    bakefile_path: Path | None, cmd: list[str], dry_run: bool
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[None]:
    return _run_uv(bakefile_path=bakefile_path, command_name="lock", cmd=cmd, dry_run=dry_run)

def run_uv_sync(
    bakefile_path: Path | None, cmd: list[str], dry_run: bool
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[None]:
    return _run_uv(bakefile_path=bakefile_path, command_name="sync", cmd=cmd, dry_run=dry_run)

def run_uv_pip(
    bakefile_path: Path | None, cmd: list[str], dry_run: bool
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[None]:
    # Special case: skip Python version check in dry_run mode
    python_path = find_python_path(bakefile_path)

    if not dry_run:
        version_result = run([str(python_path), "--version"], ...)
        console.err.print(f"Using {version}\n")

    return run_uv(("pip", *cmd, "--python", str(python_path)), dry_run=dry_run, ...)
```

### 4. Test Pattern

```python
# Tests must explicitly pass dry_run=False to all function calls
def test_with_inline_metadata(self, empty_project_folder: Path) -> None:
    bakefile_path = empty_project_folder / DEFAULT_FILE_NAME
    result = run_uv_sync(bakefile_path, [], dry_run=False)  # <-- REQUIRED
    assert result.returncode == 0

def test_dry_run(self, empty_project_folder: Path, capsys) -> None:
    bakefile_path = empty_project_folder / DEFAULT_FILE_NAME
    result = run_uv_sync(bakefile_path, [], dry_run=True)  # <-- Test dry run
    assert result.returncode == 0
    captured = capsys.readouterr()
    assert "uv sync" in captured.err
```

---

## Implementation Plan

### Phase 0: Core Infrastructure Updates

#### 0.1 Update `run()` function

**File:** `src/bake/ui/run/run.py`

**Changes:**

```python
def run(
    cmd: tuple[str, ...] | list[str],
    dry_run: bool = False,
    **kwargs: Any,
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[None]:
    """Run a command, optionally in dry run mode."""
    if dry_run:
        console.echo(f"[DRY RUN] Would run: {' '.join(str(c) for c in cmd)}")
        return subprocess.CompletedProcess(
            args=list(cmd),
            returncode=0,
            stdout="",
            stderr="",
        )

    # Existing implementation...
```

#### 0.2 Update `run_uv()` function

**File:** `src/bake/ui/run/uv.py`

**Changes:**

```python
def run_uv(
    cmd: tuple[str, ...],
    dry_run: bool = False,
    **kwargs: Any,
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[None]:
    """Run a uv command, optionally in dry run mode."""
    if dry_run:
        console.echo(f"[DRY RUN] Would run: uv {' '.join(cmd)}")
        return subprocess.CompletedProcess(
            args=["uv"] + list(cmd),
            returncode=0,
            stdout="",
            stderr="",
        )

    # Existing implementation (delegates to run())
    return run(("uv", *cmd), **kwargs)
```

#### 0.3 Add `dry_run` parameter to manage functions

**Files:** `src/bake/manage/run_uv.py`, `src/bake/manage/write_bakefile.py`, `src/bake/manage/add_inline.py`, `src/bake/manage/lint.py`

**Pattern:**

```python
def run_uv_sync(bakefile_path: Path | None, cmd: list[str], dry_run: bool = False) -> subprocess.CompletedProcess:
    # ...existing validation...

    return run_uv(
        ("sync", "--script", bakefile_path.name, *cmd),
        dry_run=dry_run,  # NEW
        capture_output=True,
        stream=True,
        check=True,
        echo=True,
        cwd=bakefile_path.parent,
    )
```

---

### Phase 1: CLI Commands (Pass dry_run through)

#### 1.1 Update `init` command

**File:** `src/bake/cli/bakefile/init.py`

**Changes:**

```python
def init(ctx: Context, ...) -> None:
    # Existing validation (unchanged)
    if ctx.obj.bakebook is not None and not force:
        console.error("Bakebook already loaded. Use --force to override.")
        raise typer.Exit(code=1)

    ctx.obj.bakefile_path = resolve_bakefile_path(chdir=ctx.obj.chdir, file_name=ctx.obj.file_name)

    if ctx.obj.bakefile_path.exists() and not force:
        console.error(f"File already exists at {ctx.obj.bakefile_path}. Use --force to overwrite.")
        raise typer.Exit(code=1)

    # Pass dry_run to write_bakefile
    write_bakefile(
        bakefile_path=ctx.obj.bakefile_path,
        bakebook_name=ctx.obj.bakebook_name,
        sample_module=simple,
        dry_run=ctx.obj.dry_run,  # NEW
    )
    ctx.obj.get_bakebook()
    assert ctx.obj.bakebook is not None

    if inline:
        if ctx.obj.dry_run:
            # Inline metadata handling needs special case for dry_run
            console.success(f"[DRY RUN] Would add PEP 723 metadata to {ctx.obj.bakefile_path}")
            return

        try:
            add_inline_metadata(ctx.obj.bakefile_path)
        except BakebookError as e:
            console.error(f"Failed to add PEP 723 metadata: {e}")
            raise typer.Exit(code=1) from None

        console.success(
            f"Successfully created bakefile with PEP 723 metadata at {ctx.obj.bakefile_path}"
        )
        return

    if not ctx.obj.dry_run:
        console.success(f"Successfully created bakefile at {ctx.obj.bakefile_path}")
```

#### 1.2 Update `add_inline` command

**File:** `src/bake/cli/bakefile/add_inline.py`

**Changes:**

```python
def add_inline(ctx: Context) -> None:
    if ctx.obj.bakefile_path is None or not ctx.obj.bakefile_path.exists():
        console.error(...)
        raise typer.Exit(code=1)

    # Pass dry_run to manage function
    add_inline_metadata(ctx.obj.bakefile_path, dry_run=ctx.obj.dry_run)
```

**In `src/bake/manage/add_inline.py`:**

```python
def add_inline_metadata(bakefile_path: Path, dry_run: bool = False) -> None:
    if dry_run:
        console.echo(f"[DRY RUN] Would add PEP 723 metadata to {bakefile_path}")
        return

    # Existing implementation...
```

#### 1.3 Update `uv sync` command

**File:** `src/bake/cli/bakefile/uv.py`

**Changes:**

```python
def sync(typer_ctx: typer.Context, ...) -> None:
    bakefile_path = typer_ctx.obj.bakefile_path
    args = list(typer_ctx.args)

    if upgrade:
        args.append("--upgrade")
    if reinstall:
        args.append("--reinstall")

    # Pass dry_run to manage function
    try:
        result = run_uv_sync(bakefile_path, args, dry_run=typer_ctx.obj.dry_run)
        raise typer.Exit(result.returncode)
    except (PythonNotFoundError, BakebookError) as e:
        console.error(str(e))
        raise typer.Exit(code=1) from None
```

#### 1.4 Update remaining UV commands

**Files:** `src/bake/cli/bakefile/uv.py` (lock, add, pip)

**Same pattern:** Add `dry_run=typer_ctx.obj.dry_run` to the manage function call.

#### 1.5 Update `lint` command

**File:** `src/bake/cli/bakefile/lint.py`

**Changes:**

```python
def lint(ctx: Context, ...) -> None:
    bakefile_path = ctx.obj.bakefile_path
    if bakefile_path is None or not bakefile_path.exists():
        console.error("Bakefile not found. Run 'bakefile init' first.")
        raise typer.Exit(code=1)

    if not any([ruff_format, ruff_check, ty_check]):
        console.warning("All linters disabled. Nothing to do.")
        raise typer.Exit(code=0)

    # Pass dry_run to lint functions
    if ruff_format:
        run_ruff_format(bakefile_path, only_bakefile, dry_run=ctx.obj.dry_run)
    if ruff_check:
        run_ruff_check(bakefile_path, only_bakefile, dry_run=ctx.obj.dry_run)
    if ty_check:
        python_path = find_python_path(bakefile_path)
        run_ty_check(bakefile_path, python_path, only_bakefile, dry_run=ctx.obj.dry_run)
```

---

## Testing Strategy

### Unit Tests

For each command, add tests:

1. **Dry run shows correct message**
    - Verify output contains "[DRY RUN]"
    - Verify action description is correct
2. **Dry run skips execution**
    - Verify file not created/modified
    - Verify external command not run
3. **Dry run still validates**
    - Verify validation errors still raise Exit(1)

### Integration Tests

Add to `tests/bake/cli/bakefile/test_bakefile_*.py`:

```python
def test_init_dry_run(self, tmp_path, run_cli):
    captured = run_cli(command="bakefile", dir_path=tmp_path, args=["-n", "init"])
    assert "[DRY RUN]" in captured.out
    assert "Would create bakefile" in captured.out
    assert not (tmp_path / "bakefile.py").exists()

def test_uv_sync_dry_run(self, examples_simple_dir, run_cli):
    captured = run_cli(command="bakefile", dir_path=examples_simple_dir, args=["-n", "uv", "sync"])
    assert "[DRY RUN]" in captured.out
    assert "Would run: uv sync" in captured.out
```

---

## Risk Assessment

| Risk                       | Probability | Impact | Mitigation                                |
| -------------------------- | ----------- | ------ | ----------------------------------------- |
| Breaking existing behavior | Low         | High   | Only skip execution, validation unchanged |
| Dry run message unclear    | Medium      | Low    | Consistent format, review wording         |
| Missing dry run check      | Low         | High   | Add tests, code review                    |
| Exit code inconsistency    | Low         | Medium | Ensure dry run returns 0                  |

---

## Success Metrics

1. **Functional:**
    - All `bakefile` commands respect `-n` / `--dry-run` flag
    - Dry run shows what would be done
    - Dry run doesn't execute side effects
    - Validation still runs in dry run mode

2. **Code Quality:**
    - All tests pass (`make test`)
    - No lint errors (`make lint`)
    - Coverage maintained

3. **User Experience:**
    - Clear, consistent dry run messages
    - No breaking changes to existing behavior
    - Flag works same way across all commands

---

## Tasks Checklist

### Phase 1: File Operations

- [ ] Update `init` command
- [ ] Add tests for `init` dry run
- [ ] Update `add_inline` command
- [ ] Add tests for `add_inline` dry run

### Phase 2: UV Commands

- [ ] Update `uv sync` command
- [ ] Add tests for `uv sync` dry run
- [ ] Update `uv lock` command
- [ ] Add tests for `uv lock` dry run
- [ ] Update `uv add` command
- [ ] Add tests for `uv add` dry run
- [ ] Update `uv pip` command
- [ ] Add tests for `uv pip` dry run

### Phase 3: Lint Command

- [ ] Update `lint` command
- [ ] Add tests for `lint` dry run

### Verification

- [ ] Run `make lint`
- [ ] Run `make test`
- [ ] Manual testing of all commands

---

## Last Updated: 2025-01-04
