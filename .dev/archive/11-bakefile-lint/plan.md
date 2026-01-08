# Plan: bakefile lint Command

**Last Updated:** 2026-01-03
**Status:** COMPLETED
**Task Number:** 11

---

## Executive Summary

Implement a `bakefile lint` command that provides a quick, optimized way to lint bakefile projects using ruff and ty. The command will offer sensible defaults for the common case while allowing users to run ruff/ty directly for advanced customization.

**Key Goal:** Make linting bakefiles as simple as `bakefile lint` while being transparent that this is a convenience wrapper.

---

## Current State Analysis

### Existing Infrastructure

1. **Makefile** - Already has a `lint` target that runs:
    - `bunx prettier` for non-Python files
    - `uv run toml-sort` for pyproject.toml
    - `uv run ruff format`
    - `uv run ruff check`
    - `uv run ty check`

2. **run() function** - `src/bake/ui/run/run.py` provides:
    - Command execution with streaming/capture
    - PTY support for color preservation
    - Exit code handling via `typer.Exit`

3. **bakefile CLI** - `src/bake/cli/bakefile/main.py`:
    - Uses `BakefileApp` base class
    - Context settings for commands with extra args
    - Pattern: manage module + CLI command file

4. **UV commands pattern** - `src/bake/manage/run_uv.py`:
    - Wrapper functions that call external tools
    - Shared helper pattern for common logic
    - Error handling with custom exceptions

### Requirements Analysis

| Requirement               | Complexity | Notes                                 |
| ------------------------- | ---------- | ------------------------------------- |
| Run ruff format           | Low        | Straightforward subprocess call       |
| Run ruff check            | Low        | Straightforward subprocess call       |
| Run ty check              | Medium     | Need to find Python path for bakefile |
| --only-bakefile flag      | Low        | Pass file to linters                  |
| Individual linter toggles | Low        | Boolean flags, conditional execution  |
| Exit code handling        | Low        | Use existing `check=True` pattern     |

---

## Proposed Future State

### User Experience

```bash
# Default: lint entire project (all Python files)
bakefile lint

# Lint only the bakefile
bakefile lint --only-bakefile
bakefile lint -b

# Skip individual linters
bakefile lint --no-ruff-format
bakefile lint --no-ruff-check
bakefile lint --no-ty

# Combine flags
bakefile lint -b --no-ty  # Only ruff on bakefile, skip type check
```

### Command Output

```
$ cd /path/to/user-project
$ bakefile lint
Running linters on project...

$ ruff format --exit-non-zero-on-format .
95 files left unchanged

$ ruff check --fix --exit-non-zero-on-fix .
All checks passed!

$ ty check --error-on-warning --python <path> bakefile.py
All checks passed!

All linters passed successfully.
```

For bakefile only:

```
$ cd /path/to/user-project
$ bakefile lint -b
Running linters on bakefile only...

$ ruff format --exit-non-zero-on-format bakefile.py
1 file reformatted

$ ruff check --fix --exit-non-zero-on-fix bakefile.py
All checks passed!

$ ty check --error-on-warning --python <path> bakefile.py
All checks passed!

All linters passed successfully.
```

---

## Implementation Phases

### Phase 1: Core Linting Functions (Manage Module)

**Goal:** Create wrapper functions for each linter using `find_ruff_bin` / `find_ty_bin`

**Tasks:**

1. Create `src/bake/manage/lint.py`
2. Implement `run_ruff_format()` function
3. Implement `run_ruff_check()` function
4. Implement `run_ty_check()` function

**Acceptance Criteria:**

- Uses `find_ruff_bin()` and `find_ty_bin()` for binary discovery
- Commands run even without global ruff/ty installation
- Follows `run_uv()` pattern: custom echo, `echo=False` in `run()` call
- Clean display showing "ruff" and "ty" instead of full binary paths
- Each function returns `subprocess.CompletedProcess`
- Functions accept `files: str | None` and `cwd: Path` parameters

### Phase 2: CLI Command

**Goal:** Create the `bakefile lint` command

**Tasks:**

1. Create `src/bake/cli/bakefile/lint.py`
2. Add typer options for flags
3. Implement main `lint()` function
4. Add section headers for each linter
5. Handle exit codes from all linters
6. Add summary message

**Acceptance Criteria:**

- Command runs all 3 linters by default
- `--only-bakefile` limits to bakefile.py
- `--no-*` flags skip individual linters
- Exit code 1 if any linter fails
- Clear section headers in output

### Phase 3: Command Registration

**Goal:** Register lint command in bakefile CLI

**Tasks:**

1. Import `lint` in `main.py`
2. Register command with `bakefile_app.command()`
3. Add help text describing the convenience nature

**Acceptance Criteria:**

- `bakefile lint` appears in help
- `bakefile lint --help` shows all options
- Command is discoverable

### Phase 4: Testing

**Goal:** Ensure reliability and correctness

**Tasks:**

1. Unit tests for `run_ruff_format()`
2. Unit tests for `run_ruff_check()`
3. Unit tests for `run_ty_check()`
4. CLI tests for default behavior
5. CLI tests for `--only-bakefile`
6. CLI tests for individual linter toggles
7. Test exit code propagation

**Acceptance Criteria:**

- All tests pass
- Coverage ≥ 80% for new code
- Exit codes properly propagate

---

## Detailed Tasks

### 1. Create `src/bake/manage/lint.py`

**Effort:** M
**Priority:** P0 (blocking)

**Specification:**

```python
import logging
import subprocess
from pathlib import Path

from ruff.__main__ import find_ruff_bin
from ty.__main__ import find_ty_bin

from bake.ui import console
from bake.ui.run import run

logger = logging.getLogger(__name__)

def run_ruff_format(
    files: str | None = None,
    *,
    cwd: Path,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run ruff format on specified files or entire project.

    Args:
        files: File pattern to lint (e.g., ".", "bakefile.py"). Defaults to ".".
        cwd: Working directory (user's project directory).
        check: If True, raise typer.Exit on non-zero exit code.

    Returns:
        CompletedProcess with linter output.
    """
    ruff_bin = find_ruff_bin()
    target = files or "."
    cmd = ["format", "--exit-non-zero-on-format", target]

    # Build display string: "ruff" + command parts (no full binary path)
    display_cmd = "ruff " + " ".join(cmd)

    # Echo command to console
    console.cmd(display_cmd)

    # Call run with full ruff binary path, echo=False (already displayed)
    return run(
        [str(ruff_bin), *cmd],
        cwd=cwd,
        capture_output=True,
        stream=True,
        check=check,
        echo=False,
    )

def run_ruff_check(
    files: str | None = None,
    *,
    cwd: Path,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run ruff check on specified files or entire project.

    Args:
        files: File pattern to lint (e.g., ".", "bakefile.py"). Defaults to ".".
        cwd: Working directory (user's project directory).
        check: If True, raise typer.Exit on non-zero exit code.

    Returns:
        CompletedProcess with linter output.
    """
    ruff_bin = find_ruff_bin()
    target = files or "."
    cmd = ["check", "--fix", "--exit-non-zero-on-fix", target]

    # Build display string: "ruff" + command parts (no full binary path)
    display_cmd = "ruff " + " ".join(cmd)

    # Echo command to console
    console.cmd(display_cmd)

    # Call run with full ruff binary path, echo=False (already displayed)
    return run(
        [str(ruff_bin), *cmd],
        cwd=cwd,
        capture_output=True,
        stream=True,
        check=check,
        echo=False,
    )

def run_ty_check(
    bakefile_path: Path,
    python_path: Path,
    *,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run ty check on bakefile with specified Python.

    Args:
        bakefile_path: Path to the bakefile.py.
        python_path: Path to Python interpreter for ty.
        check: If True, raise typer.Exit on non-zero exit code.

    Returns:
        CompletedProcess with linter output.
    """
    ty_bin = find_ty_bin()
    cmd = ["check", "--error-on-warning", "--python", str(python_path), str(bakefile_path)]

    # Build display string: "ty" + command parts (no full binary path)
    display_cmd = "ty " + " ".join(cmd)

    # Echo command to console
    console.cmd(display_cmd)

    # Call run with full ty binary path, echo=False (already displayed)
    return run(
        [str(ty_bin), *cmd],
        cwd=bakefile_path.parent,
        capture_output=True,
        stream=True,
        check=check,
        echo=False,
    )
```

**Dependencies:**

- `bake.ui.run.run()` - exists
- No new dependencies

**Acceptance Criteria:**

- Functions run correct commands
- `files=None` defaults to "." (all files)
- `files="bakefile.py"` runs only on bakefile
- `cwd=bakefile_path.parent` ensures linters run in user's project directory
- Exit codes propagate correctly

---

### 2. Create `src/bake/cli/bakefile/lint.py`

**Effort:** M
**Priority:** P0 (blocking)

**Specification:**

```python
from typing import Annotated

import typer

from bake.cli.common.context import Context
from bake.manage.find_python import find_python_path
from bake.manage.lint import run_ruff_check, run_ruff_format, run_ty_check
from bake.ui import console

# Use Typer's callback pattern for flags
def lint(
    ctx: Context,
    only_bakefile: Annotated[
        bool,
        typer.Option("--only-bakefile", "-b", help="Only lint the bakefile, not entire project"),
    ] = False,
    ruff_format: Annotated[
        bool,
        typer.Option("--ruff-format/--no-ruff-format", show_default=False),
    ] = True,
    ruff_check: Annotated[
        bool,
        typer.Option("--ruff-check/--no-ruff-check", show_default=False),
    ] = True,
    ty_check: Annotated[
        bool,
        typer.Option("--ty/--no-ty", show_default=False),
    ] = True,
) -> None:
    """
    Quick linter for bakefile projects.

    This is a simple, optimized way to lint your bakefile.
    For advanced linter configuration, use ruff and ty directly.

    By default, runs: ruff format, ruff check, ty check

    Examples:
        bakefile lint              # Lint entire project
        bakefile lint -b           # Lint only bakefile.py
        bakefile lint --no-ty      # Skip type checking
    """
    bakefile_path = ctx.obj.bakefile_path
    if bakefile_path is None or not bakefile_path.exists():
        console.error("Bakefile not found. Run 'bakefile init' first.")
        raise typer.Exit(code=1)

    files = str(bakefile_path.name) if only_bakefile else "."
    cwd = bakefile_path.parent  # Run in user's project directory

    console.info(f"Running linters on {'bakefile.py only' if only_bakefile else 'project'}...")
    console.echo()

    results = []

    # Ruff Format
    if ruff_format:
        try:
            result = run_ruff_format(files, cwd=cwd, check=True)
            results.append(("format", result.returncode))
        except typer.Exit:
            results.append(("format", 1))

    # Ruff Check
    if ruff_check:
        try:
            result = run_ruff_check(files, cwd=cwd, check=True)
            results.append(("check", result.returncode))
        except typer.Exit:
            results.append(("check", 1))

    # Ty Check
    if ty_check:
        python_path = find_python_path(bakefile_path)
        try:
            result = run_ty_check(bakefile_path, python_path, check=True)
            results.append(("ty", result.returncode))
        except typer.Exit:
            results.append(("ty", 1))

    # Summary
    console.echo()
    failed = [name for name, code in results if code != 0]
    if failed:
        console.error(f"Linters failed: {', '.join(failed)}")
        raise typer.Exit(code=1)
    else:
        console.success("All linters passed successfully.")
```

**Dependencies:**

- `bake.manage.lint` - created in task 1
- `bake.manage.find_python.find_python_path()` - exists
- `bake.ui.console` - exists

**Acceptance Criteria:**

- All flags work correctly
- Output is clear with section headers
- Exit code 1 if any linter fails
- Help text is descriptive

---

### 3. Register Command in `main.py`

**Effort:** S
**Priority:** P0 (blocking)

**Changes:**

```python
# Add import
from .lint import lint

# Register command
bakefile_app.command()(lint)
```

**Acceptance Criteria:**

- Command appears in `bakefile --help`
- `bakefile lint --help` works
- Command is accessible

---

### 4. Create Tests

**Effort:** M
**Priority:** P1 (important)

**Files to create:**

- `tests/bake/manage/test_lint.py`
- `tests/bake/cli/bakefile/test_bakefile_lint.py`

**Test cases:**

```python
# test_lint.py - Unit tests
class TestRunRuffFormat:
    def test_runs_on_project(self)
    def test_runs_on_bakefile_only(self)
    def test_propagates_exit_code(self)

class TestRunRuffCheck:
    def test_runs_on_project(self)
    def test_runs_on_bakefile_only(self)
    def test_propagates_exit_code(self)

class TestRunTyCheck:
    def test_runs_with_python_path(self)
    def test_propagates_exit_code(self)

# test_bakefile_lint.py - CLI tests
class TestBakefileLint:
    def test_default_runs_all_linters(self)
    def test_bakefile_only_flag(self)
    def test_no_ruff_format_flag(self)
    def test_no_ruff_check_flag(self)
    def test_no_ty_flag(self)
    def test_combined_flags(self)
    def test_exit_code_on_failure(self)
```

**Acceptance Criteria:**

- All tests pass
- Coverage ≥ 80%

---

## Risk Assessment and Mitigation

### Risk 1: Ruff/Ty Binary Discovery

**Risk:** `uv run ruff` may not work if ruff not installed

**Mitigation:**

- Ruff and ty are already in project dependencies
- Use `uv run` wrapper which handles this

**Residual Risk:** Low

### Risk 2: Python Path for Ty

**Risk:** `find_python_path()` may fail for bakefiles without metadata

**Mitigation:**

- ty check should only run when bakefile has valid Python
- Add graceful error handling
- Consider making ty check optional for bakefiles without PEP 723

**Residual Risk:** Low

### Risk 3: User Confusion About Scope

**Risk:** Users may expect `bakefile lint` to lint user's project files, not bakefile itself

**Mitigation:**

- Clear help text explaining what's being linted
- Default to project scope (`.`) not bakefile-only
- `--only-bakefile` flag is explicit opt-in

**Residual Risk:** Low

### Risk 4: Exit Code Handling

**Risk:** Linters may have different exit code meanings

**Mitigation:**

- Use `--exit-non-zero-on-format` for ruff format (0 = formatted, 1 = needs formatting)
- Use `--exit-non-zero-on-fix` for ruff check (0 = all fixed, 1 = unfixable issues)
- Use `--error-on-warning` for ty (0 = clean, 1 = warnings/errors)

**Residual Risk:** Low

---

## Success Metrics

1. **Functional:**
    - `bakefile lint` runs all 3 linters successfully
    - Exit codes propagate correctly
    - All flags work as expected

2. **Quality:**
    - Test coverage ≥ 80%
    - All tests pass
    - No regressions in existing tests

3. **User Experience:**
    - Clear, helpful output
    - Discoverable via help
    - Sensible defaults

---

## Required Resources and Dependencies

### Dependencies (Internal)

- `bake.ui.run.run()` - command execution
- `bake.manage.find_python.find_python_path()` - Python discovery
- `bake.ui.console` - user output
- Typer - CLI framework

### Dependencies (External)

- `ruff` - already in dev dependencies
- `ty` - already in dev dependencies
- `uv` - already in dev dependencies

**No new dependencies required.**

---

## Timeline Estimates

| Phase     | Tasks          | Effort        | Dependencies |
| --------- | -------------- | ------------- | ------------ |
| Phase 1   | Core functions | 1-2 hours     | None         |
| Phase 2   | CLI command    | 1-2 hours     | Phase 1      |
| Phase 3   | Registration   | 15 min        | Phase 2      |
| Phase 4   | Testing        | 1-2 hours     | Phase 2      |
| **Total** | **All**        | **4-7 hours** | -            |

---

## Open Questions

1. **Should we include prettier and toml-sort?**
    - Current Makefile includes them
    - Decision: No, keep it simple for Python-only linting
    - Users can run make lint for full linting

2. **Should ty check run for non-PEP 723 bakefiles?**
    - Decision: Yes, use project Python via `find_python_path()`
    - Already handles this case

3. **Should we add `--fix` flag?**
    - Ruff check already uses `--fix`
    - Ty doesn't have a fix mode
    - Decision: No, always attempt fixes for ruff

4. **What if a linter isn't installed?**
    - `uv run ruff` will install if needed
    - Should work transparently
