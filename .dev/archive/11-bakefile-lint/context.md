# Context: bakefile lint Command

**Last Updated:** 2026-01-03
**Status:** IN PROGRESS

---

## SESSION PROGRESS

### ✅ COMPLETED

- Dev docs plan created with comprehensive implementation strategy
- Technical requirements documented
- Risk assessment completed
- **Phase 1: Core Linting Functions** - `src/bake/manage/lint.py` created
    - `run_ruff()` - shared function for ruff commands
    - `run_ruff_format()` - runs ruff format with `only_bakefile` support
    - `run_ruff_check()` - runs ruff check with `only_bakefile` support
    - `run_ty_check()` - runs ty check with `only_bakefile` support
- **Phase 2: CLI Command** - `src/bake/cli/bakefile/lint.py` created
    - `--only-bakefile` / `-b` flag
    - `--ruff-format` / `--no-ruff-format` flag
    - `--ruff-check` / `--no-ruff-check` flag
    - `--ty` / `--no-ty` flag
- **Phase 3: Command Registration** - registered in `main.py`
- **Tests** - `tests/bake/manage/test_lint.py` created with 12 passing tests

### 🟡 IN PROGRESS

- Ready to start Phase 4: CLI tests (if needed)

### ⏳ NEXT STEPS

1. Manual testing of the lint command
2. Update PROJECT_KNOWLEDGE.md with lint command info

### ⚠️ BLOCKERS

- None

---

## REFERENCE MATERIAL

### Makefile lint Target (Current Implementation)

```makefile
lint:
	bunx prettier@latest --write "**/*.{ts,tsx,css,json,yaml,yml,md}"
	uv run toml-sort \
		--sort-inline-arrays --in-place \
		--sort-first=project,dependency-groups \
		pyproject.toml
	uv run ruff format --exit-non-zero-on-format .
	uv run ruff check --fix --exit-non-zero-on-fix .
	uv run ty check --error-on-warning
```

**Key observations:**

- Prettier handles non-Python files (we'll skip this)
- toml-sort handles pyproject.toml (we'll skip this)
- ruff format, ruff check, ty check are the Python linters
- All commands use `uv run` for execution

### test.py Reference (Linter Binary Discovery)

```python
from ruff.__main__ import find_ruff_bin
from ty.__main__ import find_ty_bin

print(find_ruff_bin())
print(find_ty_bin())
```

**Note:** We don't need to use these functions since we're using `uv run` wrapper which handles binary discovery automatically.

---

## KEY DESIGN DECISIONS

### 0. Working Directory: User's Project (NOT bakefile installation)

**Critical:** `bakefile lint` runs linters on the **user's project** (where their bakefile.py is located), not the bakefile installation itself.

**Implementation:**

- All linter functions receive `cwd=bakefile_path.parent`
- This ensures `.` refers to the user's project directory
- `files="bakefile.py"` refers to the user's bakefile.py (relative to cwd)

**Example:**

```bash
$ cd /path/to/user-project
$ bakefile lint
# Runs ruff/ty in /path/to/user-project/
```

Without this fix, `bakefile lint` would lint the bakefile installation directory instead of the user's project.

### 1. Pass-Through Pattern (No Option Parsing)

The lint command will NOT expose individual ruff/ty options. Instead:

```bash
# Good - simple usage
bakefile lint
bakefile lint -b

# For advanced usage - use tools directly
uv run ruff check --select F --fix .
uv run ty check --error-on-warning --python <path> bakefile.py
```

**Rationale:**

- Keeps bakefile lint simple
- Avoids option bloat
- Users can run ruff/ty directly for advanced needs
- Follows pattern established by UV commands

### 2. Scope: Project vs Bakefile-Only

**Default behavior:** Lint entire project (`.`)

```bash
bakefile lint  # Runs on all Python files in project
```

**Opt-in behavior:** Lint only bakefile

```bash
bakefile lint -b  # Runs only on bakefile.py
```

**Rationale:**

- Most users want to lint their entire codebase
- Bakefile-only is a special case for quick checks
- Flag name `--only-bakefile` / `-b` is explicit

### 3. Linter Toggle Flags

Use positive boolean flags with `--no-*` negation:

```python
ruff_format: bool = True   # --ruff-format / --no-ruff-format
ruff_check: bool = True    # --ruff-check / --no-ruff-check
ty_check: bool = True      # --ty / --no-ty
```

**Rationale:**

- Typer's built-in flag negation is clean
- Clear what's enabled by default
- Easy to skip individual linters

### 4. Exit Code Handling

**Strategy:** Exit code 1 if ANY linter fails

```python
results = []
# ... run each linter ...
failed = [name for name, code in results if code != 0]
if failed:
    console.error(f"Linters failed: {', '.join(failed)}")
    raise typer.Exit(code=1)
```

**Rationale:**

- CI/CD needs clear failure signal
- All linters must pass for success
- User sees which linters failed

### 5. Output Formatting

**Section headers for each linter:**

```
[FORMAT] ruff format --exit-non-zero-on-format .
[CHECK] ruff check --fix --exit-non-zero-on-fix .
[TYPE] ty check --error-on-warning --python <path> bakefile.py
```

**Rationale:**

- Clear which linter is running
- Matches tool name conventions
- Easy to scan output

---

## DEPENDENCIES

### Files to Create

| File                                            | Status | Purpose                  |
| ----------------------------------------------- | ------ | ------------------------ |
| `src/bake/manage/lint.py`                       | TODO   | Linter wrapper functions |
| `src/bake/cli/bakefile/lint.py`                 | TODO   | CLI command              |
| `tests/bake/manage/test_lint.py`                | TODO   | Unit tests               |
| `tests/bake/cli/bakefile/test_bakefile_lint.py` | TODO   | CLI tests                |

### Files to Modify

| File                            | Status | Purpose               |
| ------------------------------- | ------ | --------------------- |
| `src/bake/cli/bakefile/main.py` | TODO   | Register lint command |

### Existing Dependencies

| Module / Function                            | Purpose                      |
| -------------------------------------------- | ---------------------------- |
| `bake.ui.run.run()`                          | Command execution            |
| `bake.manage.find_python.find_python_path()` | Python path discovery for ty |
| `bake.ui.console`                            | User output                  |
| `bake.cli.common.context.Context`            | Typed context for CLI        |

---

## IMPLEMENTATION NOTES - Phase 1: Core Functions

### run_ruff_format()

```python
from ruff.__main__ import find_ruff_bin
from bake.ui import console
from bake.ui.run import run

def run_ruff_format(
    files: str | None = None,
    *,
    cwd: Path,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    ruff_bin = find_ruff_bin()
    target = files or "."
    cmd = ["format", "--exit-non-zero-on-format", target]

    # Build display string: "ruff" + command parts (no full binary path)
    display_cmd = "ruff " + " ".join(cmd)

    # Echo command to console (like run_uv does)
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
```

**Key points:**

- Uses `find_ruff_bin()` for binary discovery (works even without global ruff)
- `files=None` → "." (all files in cwd)
- `files="bakefile.py"` → only bakefile
- `cwd=bakefile_path.parent` → user's project directory (important!)
- Follows `run_uv()` pattern: custom `console.cmd()`, `echo=False` in `run()` call
- `check=True` raises `typer.Exit` on failure

### run_ruff_check()

```python
from ruff.__main__ import find_ruff_bin
from bake.ui import console
from bake.ui.run import run

def run_ruff_check(
    files: str | None = None,
    *,
    cwd: Path,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    ruff_bin = find_ruff_bin()
    target = files or "."
    cmd = ["check", "--fix", "--exit-non-zero-on-fix", target]

    display_cmd = "ruff " + " ".join(cmd)
    console.cmd(display_cmd)

    return run(
        [str(ruff_bin), *cmd],
        cwd=cwd,
        capture_output=True,
        stream=True,
        check=check,
        echo=False,
    )
```

**Key points:**

- Uses `find_ruff_bin()` for binary discovery
- Always runs with `--fix` (auto-fix issues)
- `--exit-non-zero-on-fix` means 1 = unfixable issues remain
- `cwd=bakefile_path.parent` → user's project directory (important!)

### run_ty_check()

```python
from ty.__main__ import find_ty_bin
from bake.ui import console
from bake.ui.run import run

def run_ty_check(
    bakefile_path: Path,
    python_path: Path,
    *,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    ty_bin = find_ty_bin()
    cmd = ["check", "--error-on-warning", "--python", str(python_path), str(bakefile_path)]

    display_cmd = "ty " + " ".join(cmd)
    console.cmd(display_cmd)

    return run(
        [str(ty_bin), *cmd],
        cwd=bakefile_path.parent,
        capture_output=True,
        stream=True,
        check=check,
        echo=False,
    )
```

**Key points:**

- Uses `find_ty_bin()` for binary discovery (works even without global ty)
- Requires `bakefile_path` (always type-check bakefile.py)
- Requires `python_path` (from `find_python_path()`)
- `cwd=bakefile_path.parent` → user's project directory (important!)
- Uses `--error-on-warning` for strict checking

---

## COMMAND LINE INTERFACE

### Help Text

```
Usage: bakefile lint [OPTIONS]

  Quick linter for bakefile projects.

  This is a simple, optimized way to lint your bakefile. For advanced
  linter configuration, use ruff and ty directly.

  By default, runs: ruff format, ruff check, ty check

Options:
  -b, --only-bakefile          Only lint the bakefile, not entire project
  --ruff-format / --no-ruff-format  Enable/disable ruff format
  --ruff-check / --no-ruff-check    Enable/disable ruff check
  --ty / --no-ty                Enable/disable ty check
  --help                        Show this message and exit
```

### Example Usage

```bash
# Default: lint all files
bakefile lint

# Only bakefile
bakefile lint -b

# Skip type checking
bakefile lint --no-ty

# Only run ruff, skip ty
bakefile lint --no-ty

# Debug: see what would run
bakefile lint --dry-run  # (future enhancement?)
```

---

## TESTING STRATEGY

### Unit Tests (test_lint.py)

Test each function in isolation:

```python
class TestRunRuffFormat:
    def test_runs_on_project(self, empty_project_folder):
        result = run_ruff_format(files=".")
        assert result.returncode == 0

    def test_runs_on_bakefile_only(self, empty_project_folder):
        result = run_ruff_format(files="bakefile.py")
        assert result.returncode == 0

    def test_propagates_exit_code(self, empty_project_folder_with_errors):
        with pytest.raises(typer.Exit):
            run_ruff_format(files="bad.py", check=True)
```

### CLI Tests (test_bakefile_lint.py)

Test end-to-end CLI behavior:

```python
class TestBakefileLint:
    def test_default_runs_all_linters(self, empty_project_folder, run_cli):
        result = run_cli(CMD_BAKEFILE, dir_path=empty_project_folder, args=["lint"])
        assert result.exit_code == 0
        assert "[FORMAT]" in result.err
        assert "[CHECK]" in result.err
        assert "[TYPE]" in result.err

    def test_bakefile_only_flag(self, empty_project_folder, run_cli):
        result = run_cli(CMD_BAKEFILE, dir_path=empty_project_folder, args=["lint", "-b"])
        assert result.exit_code == 0
        # Verify only bakefile was linted

    def test_no_ty_flag(self, empty_project_folder, run_cli):
        result = run_cli(CMD_BAKEFILE, dir_path=empty_project_folder, args=["lint", "--no-ty"])
        assert result.exit_code == 0
        assert "[TYPE]" not in result.err
```

---

## EDGE CASES

### 1. Bakefile Not Found

**Behavior:** Show error, exit code 1

```python
if bakefile_path is None or not bakefile_path.exists():
    console.error("Bakefile not found. Run 'bakefile init' first.")
    raise typer.Exit(code=1)
```

### 2. Python Path Not Found (for ty)

**Behavior:** `find_python_path()` will raise `PythonNotFoundError`

**Handling:** Let it propagate, user gets clear error message

### 3. Linter Not Installed

**Behavior:** `uv run ruff` will auto-install if in dependencies

**Fallback:** If ruff/ty not in pyproject.toml, uv will fail with clear message

### 4. All Linters Disabled

**Behavior:** Show warning if all flags are `--no-*`

```python
if not any([ruff_format, ruff_check, ty_check]):
    console.warning("All linters disabled. Nothing to do.")
    raise typer.Exit(code=0)
```

---

## FUTURE ENHANCEMENTS (Out of Scope)

- `--dry-run` flag to show what would run
- `--verbose` flag for detailed output
- Custom ruff/ty config file paths
- Parallel linter execution
- Custom file glob patterns
- Integration with pre-commit hooks
