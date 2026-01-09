# Bakefile Dependency Management Commands

**Last Updated:** 2025-12-31

## Executive Summary

Implement `bakefile pip/add/lock/sync` commands as thin pass-through wrappers around `uv`. These commands automatically inject Python paths (`--python`) or script context (`--script`), then forward all arguments directly to uv. No need to replicate uv's option parsing - uv handles everything.

## Current State Analysis

### Existing Infrastructure

- `bakefile find-python` command exists (returns Python path for bakefile)
- `bake.manage.find_python.find_python()` - returns `Path` to Python interpreter
- `bake.utils.subprocess.run_uv()` - wrapper for running uv commands
- CLI pattern established in `src/bake/cli/bakefile/`

### What's Missing

- No `pip` command for managing packages via `uv pip`
- No `add` command for adding dependencies via `uv add --script`
- No `lock` command for locking dependencies via `uv lock --script`
- No `sync` command for syncing environment via `uv sync --script`

## Proposed Future State

### Command Interface

```bash
# Pip commands - works for both inline & project-level
bakefile pip install requests
bakefile pip install -r requirements.txt
bakefile pip list --format=json
bakefile pip freeze
bakefile pip show requests
bakefile pip tree

# Add - only for bakefiles with PEP 723 inline metadata
bakefile add requests
bakefile add "requests>=2.32.0" --dev
bakefile add -r requirements.txt

# Lock - only for bakefiles with PEP 723 inline metadata
bakefile lock
bakefile lock --upgrade
bakefile lock -U

# Sync - only for bakefiles with PEP 723 inline metadata
bakefile sync
bakefile sync --frozen
bakefile sync --no-dev
```

### Key Design Decisions

1. **Pass-through pattern**: No option parsing in bakefile - just pass args to uv
2. **Command separation**:
    - `pip` - works for both inline and project-level (uses `--python`)
    - `add/lock/sync` - only for inline metadata (uses `--script`)
3. **Error handling**: For `add/lock/sync`, validate inline metadata exists and error with helpful message

### Architecture

```
src/bake/
├── manage/
│   ├── __init__.py
│   ├── find_python.py          # (exists)
│   ├── pip.py                  # NEW: single run_pip() function
│   ├── add.py                  # NEW: single add_dependencies() function
│   ├── lock.py                 # NEW: single lock_dependencies() function
│   └── sync.py                 # NEW: single sync_environment() function
└── cli/
    └── bakefile/
        ├── __init__.py
        ├── main.py             # (register new commands)
        ├── find_python.py      # (exists)
        ├── pip.py              # NEW: CLI command (pass-through)
        ├── add.py              # NEW: CLI command (pass-through)
        ├── lock.py             # NEW: CLI command (pass-through)
        └── sync.py             # NEW: CLI command (pass-through)
```

## Implementation Phases

### Phase 1: Core Infrastructure

1. Create `bake.manage.pip` module (single function)
2. Create `bake.manage.add` module (single function)
3. Create `bake.manage.lock` module (single function)
4. Create `bake.manage.sync` module (single function)

### Phase 2: CLI Commands

1. Create `bakefile pip` command
2. Create `bakefile add` command
3. Create `bakefile lock` command
4. Create `bakefile sync` command

### Phase 3: Testing & Documentation

1. Write unit tests for each module
2. Write CLI tests for each command
3. Update documentation

## Detailed Tasks

### Phase 1: Core Infrastructure

#### 1.1 Create `bake.manage.pip` module

- **Effort**: S
- **Function**: Single pass-through to `uv pip` with `--python`
- **Key Function**:
    ```python
    def run_pip(python_path: Path, *args: str) -> CompletedProcess:
        """Run uv pip command with Python path."""
        return run_uv("pip", *args, "--python", str(python_path))
    ```
- **Acceptance Criteria**:
    - Uses `run_uv()` with individual string args
    - `--python` passed as separate arg
    - All user args passed through unchanged

#### 1.2 Create `bake.manage.add` module

- **Effort**: S
- **Function**: Pass-through to `uv add --script` with validation
- **Key Function**:
    ```python
    def add_dependencies(bakefile_path: Path, *args: str) -> CompletedProcess:
        """Add dependencies to bakefile (requires PEP 723 metadata)."""
        if not _has_inline_metadata(bakefile_path):
            raise BakebookError("...")
        return run_uv("add", "--script", bakefile_path.name, *args,
                      cwd=bakefile_path.parent)
    ```
- **Acceptance Criteria**:
    - Uses `_has_inline_metadata()` from `find_python.py`
    - Uses `run_uv()` with individual string args
    - `--script` passed as separate arg
    - Runs in `bakefile_path.parent` directory

#### 1.3 Create `bake.manage.lock` module

- **Effort**: S
- **Function**: Pass-through to `uv lock --script` with validation
- **Key Function**:
    ```python
    def lock_dependencies(bakefile_path: Path, *args: str) -> CompletedProcess:
        """Lock bakefile dependencies (requires PEP 723 metadata)."""
        if not _has_inline_metadata(bakefile_path):
            raise BakebookError("...")
        return run_uv("lock", "--script", bakefile_path.name, *args,
                      cwd=bakefile_path.parent)
    ```
- **Acceptance Criteria**:
    - Same validation pattern as `add`
    - Uses `run_uv()` with individual string args

#### 1.4 Create `bake.manage.sync` module

- **Effort**: S
- **Function**: Pass-through to `uv sync --script` with validation
- **Key Function**:
    ```python
    def sync_environment(bakefile_path: Path, *args: str) -> CompletedProcess:
        """Sync bakefile environment (requires PEP 723 metadata)."""
        if not _has_inline_metadata(bakefile_path):
            raise BakebookError("...")
        return run_uv("sync", "--script", bakefile_path.name, *args,
                      cwd=bakefile_path.parent)
    ```
- **Acceptance Criteria**:
    - Same validation pattern as `add`
    - Uses `run_uv()` with individual string args

### Phase 2: CLI Commands

#### 2.1 Create `bakefile pip` command

- **Effort**: S
- **File**: `src/bake/cli/bakefile/pip.py`
- **Pattern**:
    ```python
    def pip(
        ctx: Context,
        args: list[str] = typer.Argument(...),
    ) -> None:
        python_path = find_python_path(ctx.obj.bakefile_path)
        run_pip(python_path, *args)
    ```
- **Acceptance Criteria**:
    - Uses `typer.Argument(...)` to capture all args
    - Calls `find_python()` then `run_pip()`
    - No metadata validation (works for both types)

#### 2.2 Create `bakefile add` command

- **Effort**: S
- **File**: `src/bake/cli/bakefile/add.py`
- **Pattern**:
    ```python
    def add(
        ctx: Context,
        args: list[str] = typer.Argument(...),
    ) -> None:
        python_path = find_python_path(ctx.obj.bakefile_path)
        add_dependencies(ctx.obj.bakefile_path, *args)
    ```
- **Acceptance Criteria**:
    - Validation happens in `add_dependencies()`
    - Clear error message if no inline metadata

#### 2.3 Create `bakefile lock` command

- **Effort**: S
- **File**: `src/bake/cli/bakefile/lock.py`
- **Acceptance Criteria**:
    - Same pattern as `add`
    - Validation in `lock_dependencies()`

#### 2.4 Create `bakefile sync` command

- **Effort**: S
- **File**: `src/bake/cli/bakefile/sync.py`
- **Acceptance Criteria**:
    - Same pattern as `add`
    - Validation in `sync_environment()`

#### 2.5 Register commands in main.py

- [ ] Import all command modules
- [ ] Register each with `bakefile_app.command()`

### Phase 3: Testing & Documentation

#### 3.1 Write unit tests

- **Effort**: M
- **Coverage**: All new `bake.manage.*` modules
- **Acceptance Criteria**:
    - Mock `run_uv()` calls
    - Verify correct args passed (as individual strings)
    - Test validation for `add/lock/sync`

#### 3.2 Write CLI tests

- **Effort**: M
- **Coverage**: All new CLI commands
- **Acceptance Criteria**:
    - Use CliRunner from typer.testing
    - Test arg pass-through works
    - Test error cases

#### 3.3 Update documentation

- **Effort**: S
- **Files**: README.md, CLAUDE.md
- **Acceptance Criteria**:
    - Document new commands
    - Note that `add/lock/sync` require inline metadata
    - Provide usage examples

## Risk Assessment and Mitigation

| Risk                                            | Impact | Likelihood | Mitigation                                                |
| ----------------------------------------------- | ------ | ---------- | --------------------------------------------------------- |
| uv CLI changes break compatibility              | Low    | Low        | Pass-through means we adapt automatically                 |
| PEP 723 metadata missing for add/lock/sync      | Medium | High       | Clear error message suggesting `uv add` for project-level |
| User confusion about when to use bakefile vs uv | Low    | Medium     | Clear documentation; error messages guide users           |

## Success Metrics

1. All 4 commands functional (`pip`, `add`, `lock`, `sync`)
2. Test coverage ≥ 80% for new code
3. All linters pass (ruff, mypy, ty)
4. Documentation updated

## Required Resources and Dependencies

- `uv` installed (already required)
- Existing `find_python()` function
- Existing `run_uv()` wrapper
- Existing `_has_inline_metadata()` function
- typer for CLI
- pytest for testing

## Command Behavior Summary

| Command         | Works On              | UV Args Injected         | User Args          |
| --------------- | --------------------- | ------------------------ | ------------------ |
| `bakefile pip`  | Both inline & project | `--python <path>`        | All passed through |
| `bakefile add`  | Inline metadata only  | `--script <bakefile.py>` | All passed through |
| `bakefile lock` | Inline metadata only  | `--script <bakefile.py>` | All passed through |
| `bakefile sync` | Inline metadata only  | `--script <bakefile.py>` | All passed through |

## Error Message Example

When user runs `bakefile add` without inline metadata:

```
error: bakefile add requires PEP 723 inline metadata.
Run 'bakefile add-inline' to add metadata, or use 'uv add' for project-level dependencies.
```

## Dependencies

- Depends on: `find_python` (complete)
- Blocks by: None
- Parallel with: None recommended (implement sequentially)
