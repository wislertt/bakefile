# Tasks: Bakefile Dependency Management Commands

**Last Updated:** 2026-01-02

## Command 1: pip ✅ COMPLETE

### 1.1 Create `bake.manage.pip` module

- [x] Create `src/bake/manage/run_uv_pip.py` (note: different name than planned)
- [x] Implement `run_uv_pip(bakefile_path: Path | None, cmd: list[str])`
- [x] Use `run_uv(("pip", *cmd, "--python", str(python_path)))`
- [x] Add logging
- [x] Show Python version to user
- [x] Display warning for project-level (no inline metadata)

### 1.2 Create `bakefile pip` command

- [x] Create `src/bake/cli/bakefile/pip.py`
- [x] Use `Literal` type for pip subcommands (compile, sync, install, etc.)
- [x] Capture subcommand + args via `typer_ctx.args`
- [x] Call `run_uv_pip(bakefile_path, cmd)`
- [x] No metadata validation (works for both types)

### 1.3 Register pip command

- [x] Import `pip` in `main.py`
- [x] Register with `bakefile_app.command()` and context settings
- [x] Command appears in `bakefile --help`

### 1.4 Test pip command

- [x] Manual test: `bakefile pip list`
- [x] Manual test: `bakefile pip install <package>`
- [x] Manual test: `bakefile pip freeze`

## Command 2: add ✅ COMPLETE

### 2.1 Create `bake.manage.add` module

- [x] Create `src/bake/manage/run_uv_add.py` (note: different name than planned)
- [x] Reuse `_has_inline_metadata()` from `find_python.py`
- [x] Implement `run_uv_add(bakefile_path: Path | None, cmd: list[str])`
- [x] Validate inline metadata exists (raises error if missing)
- [x] Use `run_uv(("add", "--script", bakefile_path.name, *cmd), cwd=...)`
- [x] Add helpful error message for missing metadata
- [x] Add success message after adding dependencies
- [x] Add unit tests (3 tests, 100% coverage)

### 2.2 Create `bakefile add` command

- [x] Create `src/bake/cli/bakefile/add.py`
- [x] Use `typer_ctx.args` to capture all args
- [x] Call `run_uv_add(ctx.obj.bakefile_path, args)`
- [x] Wrap in try/except for `BakebookError` and `PythonNotFoundError`
- [x] Show error message on failure

### 2.3 Register add command

- [x] Import `add` in `main.py`
- [x] Register with `bakefile_app.command()` and context settings
- [x] Command appears in `bakefile --help`

### 2.4 Test add command

- [x] CLI test: `bakefile add typing-extensions` (with inline metadata)
- [x] CLI test: `bakefile add requests` (without inline metadata - errors)
- [x] CLI test: `bakefile add requests` (no bakefile - errors)

## Command 3: lock ✅ COMPLETE

### 3.1 Create `bake.manage.lock` module

- [x] Create `src/bake/manage/run_uv_lock.py`
- [x] Use shared `_validate_bakefile_for_script_command()` from `find_python.py`
- [x] Implement `run_uv_lock(bakefile_path: Path | None, cmd: list[str])`
- [x] Validate inline metadata exists (raises error if missing)
- [x] Use `run_uv(("lock", "--script", bakefile_path.name, *cmd), cwd=...)`
- [x] Add helpful error message for missing metadata
- [x] Refactor: Created shared validation function to reduce duplication

### 3.2 Create `bakefile lock` command

- [x] Create `src/bake/cli/bakefile/lock.py`
- [x] Use `typer_ctx.args` to capture all args
- [x] Call `run_uv_lock(ctx.obj.bakefile_path, args)`
- [x] Wrap in try/except for `BakebookError` and `PythonNotFoundError`
- [x] Show error message on failure

### 3.3 Register lock command

- [x] Import `lock` in `main.py`
- [x] Register with `bakefile_app.command()` and context settings
- [x] Command appears in `bakefile --help`

### 3.4 Test lock command

- [x] Unit tests: 3 tests (100% coverage)
- [x] CLI tests: 3 tests
- [x] Manual test: `bakefile lock` works with inline metadata

## Command 4: sync ✅ COMPLETE

### 4.1 Create `bake.manage.sync` module

- [x] Add `run_uv_sync` to `src/bake/manage/run_uv.py`
- [x] Implement `run_uv_sync(bakefile_path: Path | None, cmd: list[str])`
- [x] Validate inline metadata exists (via shared `_run_uv`)
- [x] Use `run_uv(("sync", "--script", bakefile_path.name, *cmd), cwd=...)`
- [x] Add helpful error message for missing metadata

### 4.2 Create `bakefile sync` command

- [x] Create `src/bake/cli/bakefile/sync.py`
- [x] Use `typer_ctx.args` to capture all args
- [x] Call `run_uv_sync(ctx.obj.bakefile_path, args)`
- [x] Wrap in try/except for `BakebookError` and `PythonNotFoundError`
- [x] Show error message on failure

### 4.3 Register sync command

- [x] Import `sync` in `main.py`
- [x] Register with `bakefile_app.command()` and context settings

### 4.4 Test sync command

- [x] Run `make lint` - passes
- [x] Run `make test` - 661 tests pass
- [x] Verify `bakefile --help` shows sync command

## Phase 3: Testing & Documentation

### 3.1 Unit tests for manage modules

- [ ] Create `tests/bake/manage/test_pip.py`
- [ ] Create `tests/bake/manage/test_add.py`
- [ ] Create `tests/bake/manage/test_lock.py`
- [ ] Create `tests/bake/manage/test_sync.py`
- [ ] Mock `run_uv()` in tests
- [ ] Verify correct args passed (as individual strings)
- [ ] Test validation for `add/lock/sync`
- [ ] Test error messages

### 3.2 CLI tests

- [ ] Create `tests/bake/cli/bakefile/test_pip.py`
- [ ] Create `tests/bake/cli/bakefile/test_add.py`
- [ ] Create `tests/bake/cli/bakefile/test_lock.py`
- [ ] Create `tests/bake/cli/bakefile/test_sync.py`
- [ ] Test arg pass-through works
- [ ] Test error cases (missing metadata)
- [ ] Test success messages

### 3.3 Documentation

- [ ] Update README.md with new commands
- [ ] Note that `add/lock/sync` require inline metadata
- [ ] Provide usage examples
- [ ] Update CLAUDE.md if needed

## Verification

- [ ] All tests pass
- [ ] `make lint` passes
- [ ] `make test` passes with ≥80% coverage
- [ ] Manual testing:
    - [ ] `bakefile pip install requests` works
    - [ ] `bakefile pip list` works
    - [ ] `bakefile add requests` works (with inline metadata)
    - [ ] `bakefile add requests` fails (without inline metadata)
    - [ ] `bakefile lock` works (with inline metadata)
    - [ ] `bakefile sync` works (with inline metadata)
