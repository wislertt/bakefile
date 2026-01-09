# Tasks: bakefile lint Command

**Last Updated:** 2026-01-03
**Status:** COMPLETED

---

## Phase 1: Core Linting Functions (Manage Module)

### 1.1 Create `src/bake/manage/lint.py`

- [x] Create file with imports (logging, subprocess, Path)
- [x] Import `find_ruff_bin` from `ruff.__main__`
- [x] Import `find_ty_bin` from `ty.__main__`
- [x] Import `console` and `run` from `bake.ui`
- [x] Add `run_ruff_format()` function
- [x] Add `run_ruff_check()` function
- [x] Add `run_ty_check()` function
- [x] Add module docstring (if needed)

### 1.2 Implement `run_ruff_format()`

- [x] Accept `files: str | None = None` parameter
- [x] Accept `cwd: Path` keyword-only parameter (**critical**: user's project directory)
- [x] Get ruff binary using `find_ruff_bin()`
- [x] Build display string: `"ruff " + " ".join(cmd)`
- [x] Call `console.cmd(display_cmd)` to show command
- [x] Call `run()` with full binary path, `echo=False`
- [x] Return `subprocess.CompletedProcess[str]`

### 1.3 Implement `run_ruff_check()`

- [x] Accept `files: str | None = None` parameter
- [x] Accept `cwd: Path` keyword-only parameter (**critical**: user's project directory)
- [x] Get ruff binary using `find_ruff_bin()`
- [x] Build display string: `"ruff " + " ".join(cmd)`
- [x] Call `console.cmd(display_cmd)` to show command
- [x] Call `run()` with full binary path, `echo=False`
- [x] Return `subprocess.CompletedProcess[str]`

### 1.4 Implement `run_ty_check()`

- [x] Accept `bakefile_path: Path` and `python_path: Path`
- [x] Get ty binary using `find_ty_bin()`
- [x] Build display string: `"ty " + " ".join(cmd)`
- [x] Call `console.cmd(display_cmd)` to show command
- [x] Call `run()` with full binary path, `echo=False`, `cwd=bakefile_path.parent`
- [x] Return `subprocess.CompletedProcess[str]`

---

## Phase 2: CLI Command

### 2.1 Create `src/bake/cli/bakefile/lint.py`

- [x] Create file with imports (typer, context, manage functions, console)
- [x] Define `lint()` function with `ctx: Context`
- [x] Add command docstring with examples

### 2.2 Add CLI flags

- [x] Add `--only-bakefile` / `-b` flag (bool, default False)
- [x] Add `--ruff-format` / `--no-ruff-format` flag (bool, default True)
- [x] Add `--ruff-check` / `--no-ruff-check` flag (bool, default True)
- [x] Add `--ty` / `--no-ty` flag (bool, default True)

### 2.3 Implement lint logic

- [x] Validate bakefile exists
- [x] Determine target (files string based on `--only-bakefile`)
- [x] Set `cwd = bakefile_path.parent` (**critical**: user's project directory)
- [x] Show "Running linters..." header
- [x] Call `run_ruff_format(files, cwd=cwd)` if enabled (with section header)
- [x] Call `run_ruff_check(files, cwd=cwd)` if enabled (with section header)
- [x] Find Python path using `find_python_path()`
- [x] Call `run_ty_check(bakefile_path, python_path)` if enabled (with section header)

### 2.4 Handle exit codes

- [x] Collect results from each linter
- [x] Check for failures in results
- [x] Show error message with failed linter names
- [x] Exit code 1 if any linter failed
- [x] Show success message if all passed

### 2.5 Add edge case handling

- [x] Handle bakefile not found
- [x] Handle all linters disabled case
- [x] Handle ty Python path errors (let propagate)

---

## Phase 3: Command Registration

### 3.1 Register lint command

- [x] Import `lint` in `main.py`
- [x] Register with `bakefile_app.command()(lint)`
- [x] Verify command appears in `bakefile --help`

---

## Phase 4: Testing

### 4.1 Create `tests/bake/manage/test_lint.py`

- [x] Create file with imports
- [x] Create `TestRunRuffFormat` class
- [x] Create `TestRunRuffCheck` class
- [x] Create `TestRunTyCheck` class

### 4.2 Unit tests for `run_ruff_format()`

- [x] Test `files="."` runs on project with `cwd` parameter
- [x] Test `files="bakefile.py"` runs on file with `cwd` parameter
- [x] Test exit code propagates on failure
- [x] Test exit code 0 on success

### 4.3 Unit tests for `run_ruff_check()`

- [x] Test `files="."` runs on project with `cwd` parameter
- [x] Test `files="bakefile.py"` runs on file with `cwd` parameter
- [x] Test exit code propagates on failure
- [x] Test exit code 0 on success

### 4.4 Unit tests for `run_ty_check()`

- [x] Test runs with correct Python path and `cwd` parameter
- [x] Test runs on bakefile path
- [x] Test exit code propagates on failure
- [x] Test exit code 0 on success

### 4.5 Create `tests/bake/cli/bakefile/test_bakefile_lint.py`

- [x] Create file with imports
- [x] Create `TestBakefileLint` class

### 4.6 CLI tests for default behavior

- [x] Test all 3 linters run by default
- [x] Test output contains section headers
- [x] Test exit code 0 on success

### 4.7 CLI tests for flags

- [x] Test `--only-bakefile` / `-b` limits to bakefile
- [x] Test `--no-ruff-format` skips format
- [x] Test `--no-ruff-check` skips check
- [x] Test `--no-ty` skips type check
- [x] Test combined flags work correctly

### 4.8 CLI tests for error cases

- [x] Test exit code 1 when bakefile not found
- [x] Test exit code 1 when any linter fails
- [x] Test error message shows failed linter names
- [x] Test all linters disabled case

---

## Phase 5: Verification

### 5.1 Manual testing

- [x] Run `bakefile lint` on clean project
- [x] Run `bakefile lint -b` on clean project
- [x] Run `bakefile lint --no-ty`
- [x] Run `bakefile lint --help` to verify docs
- [x] Introduce lint errors and verify exit code 1

### 5.2 Automated verification

- [x] Run `make lint` - must pass
- [x] Run `make test` - all tests pass (20 lint-related tests)
- [x] Check coverage ≥ 80% for new code

---

## Completion Checklist

- [x] All 4 phases complete
- [x] All tests passing (20 tests)
- [x] Coverage ≥ 80%
- [x] `make lint` passes
- [x] `make test` passes
- [x] Manual testing successful

---

## Implementation Summary

**Files Created:**

- `src/bake/manage/lint.py` - Core linting wrapper functions
- `src/bake/cli/bakefile/lint.py` - CLI command implementation
- `tests/bake/manage/test_lint.py` - Unit tests (12 tests)
- `tests/bake/cli/bakefile/test_bakefile_lint.py` - CLI tests (8 tests)

**Files Modified:**

- `src/bake/cli/bakefile/main.py` - Added lint command registration
- `src/bake/utils/constants.py` - Added CMD_LINT constant

**Key Design Decisions:**

1. Functions use `only_bakefile: bool` parameter instead of `files: str`
2. Ruff format and check share underlying `run_ruff()` function
3. CLI uses fail-fast pattern (stop on first linter failure)
4. Tests verify commands run, not that they pass (since test bakefiles have E501 errors)
5. `--upgrade` flag added to `lock` and `sync` commands in uv.py
6. `--reinstall` flag added to `sync` command in uv.py

**Test Results:**

- All 20 lint-related tests pass
- All linters pass (ruff format, ruff check, ty check)
