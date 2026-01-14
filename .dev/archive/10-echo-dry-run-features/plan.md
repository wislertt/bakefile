# Plan: Add Echo and Dry-Run Features to Run Module

**Last Updated:** 2026-01-02 (Phase 1-5 complete)

## Executive Summary

Add `echo` and `dry_run` parameters to the `run()` function, implement a new `run_script()` function for displaying and executing multi-line shell scripts with proper formatting, and add independent echo functionality to `run_uv()` that displays only "uv" instead of the full binary path. This will provide users with better visibility into commands being executed and the ability to preview commands without running them.

## Current State Analysis

### Existing Components

1. **`run()` function** (`src/bake/ui/run/run.py`)
    - Executes commands with streaming and output capture
    - Supports PTY on Unix for color preservation
    - Has no display/echo capability
    - No dry-run mode

2. **Console module** (`src/bake/ui/console.py`)
    - `cmd()` — displays single command with `❯` prefix
    - `script_block()` — displays multi-line shell scripts in bordered box
    - Uses `beautysh` for shell script formatting
    - Outputs to stderr

3. **`run_uv()` function** (`src/bake/ui/run/uv.py`)
    - Wraps `run()` for uv commands
    - Finds uv binary path via `find_uv_bin()`
    - Currently passes all args to `run()` without display
    - No independent echo/dry_run support

4. **Gap Analysis**
    - No way to preview commands before execution
    - No way to execute multi-line shell scripts with proper display
    - No integration between run execution and console display
    - `run_uv()` shows full binary path when echoing (not user-friendly)

## Proposed Future State

### New Features

1. **`run()` enhancements:**
    - Add `echo: bool = True` parameter — display command via `console.cmd()`
    - Add `dry_run: bool = False` parameter — skip execution, return success
    - Independent control: `dry_run` does NOT auto-echo (user combines manually)

2. **New `run_script()` function:**
    - `title: str` — script title for display
    - `script: str` — multi-line shell script
    - Same explicit params as `run()` (capture_output, check, cwd, stream, echo, dry_run)
    - Uses `console.script_block()` for display
    - Calls `run()` internally with `echo=False` (already displayed)
    - Always uses `shell=True` (scripts are shell commands)

3. **`run_uv()` enhancements:**
    - Add `echo: bool = True` parameter — independent from `run()`'s echo
    - Displays only `"uv"` prefix, not full binary path
    - Has its own `dry_run: bool = False` parameter
    - Formats display as: `console.cmd("uv " + " ".join(cmd))`
    - Passes through to `run()` with proper binary path

### API Design

```python
# Single command
run("uv pip install requests")                    # echo=True, shows + runs
run("uv pip install requests", echo=False)        # silent + runs
run("uv pip install requests", dry_run=True)       # silent + skip
run("uv pip install requests", echo=True, dry_run=True)  # show + skip

# Multi-line script
run_script("Install", "uv pip install requests")  # shows + runs
run_script("Install", "...", echo=False)          # silent + runs
run_script("Install", "...", dry_run=True)         # silent + skip
run_script("Install", "...", echo=True, dry_run=True)  # show + skip

# UV commands
run_uv(["pip", "install", "requests"])            # shows "uv pip install..." + runs
run_uv(["pip", "install", "requests"], echo=False)  # silent + runs
run_uv(["pip", "install", "requests"], dry_run=True)  # silent + skip
run_uv(["pip", "install", "requests"], echo=True, dry_run=True)  # show + skip
```

### Behavior Matrix

| echo | dry_run | Result        |
| ---- | ------- | ------------- |
| T    | F       | Show + Run    |
| T    | T       | Show + Skip   |
| F    | F       | Silent + Run  |
| F    | T       | Silent + Skip |

## Implementation Phases

### Phase 1: Update `run()` Function ✅ **COMPLETE**

**Location:** `src/bake/ui/run/run.py`

**Tasks:**

1. Add `echo` and `dry_run` parameters to function signature
2. Implement echo logic using `console.cmd()`
3. Implement dry_run logic with early return
4. Update all overload signatures
5. Update docstring with new parameters and examples

**✅ VALIDATION PASSED:**

- All linting checks passed
- All tests pass (641 tests, 93% coverage)
- Refactored into helper functions for better readability
- Changed from `subprocess.CalledProcessError` to `typer.Exit`
- Added debug logging for dry-run and error conditions

**Additional Improvements:**

- Refactored from ~190 lines into 10 focused helper functions
- Made parameters keyword-only with `*` after `cmd`
- Removed small docstrings (per project policy)
- Used explicit `key=value` format for helper calls
- Updated all existing calls to use `echo=False` for backward compatibility

### Phase 2: Update `run_uv()` Function ✅ **COMPLETE**

**Location:** `src/bake/ui/run/uv.py`

**Tasks:**

1. Add `echo` and `dry_run` parameters to function signature
2. Implement echo logic using `console.cmd()` with `"uv"` prefix only
3. Implement dry_run logic with early return
4. Update both overload signatures
5. Add comprehensive docstring
6. Pass through to `run()` with `echo=False` (independent echo)

**✅ VALIDATION PASSED:**

- All linting checks passed
- All tests pass (641 tests, 93% coverage)
- Echo displays "uv" prefix only (not full binary path)
- Passes `dry_run` through to `run()` instead of handling early
- Removed docstring (per project policy)

### Phase 3: Implement `run_script()` Function ✅ **COMPLETE**

**Location:** `src/bake/ui/run/script.py`

**Tasks:**

1. Create `run_script()` function with full signature
2. Implement echo logic using `console.script_block()`
3. Implement dry_run logic with early return
4. Call `run()` internally with `echo=False`
5. Add comprehensive docstring with examples

**✅ VALIDATION PASSED:**

- All linting checks passed
- All tests pass (649 tests, 93% coverage)
- Exported in `__init__.py` as `run_script`
- Return type matches `run()` for consistency
- Moved to separate file `script.py`
- No docstring (per project policy)

### Phase 4: Update Tests ✅ **COMPLETE**

**Location:** `tests/bake/ui/run/test_script.py`

**Tasks:**

1. Add tests for `run_script()` with echo/dry_run combinations
2. Run full test suite and fix any failing tests

**✅ VALIDATION PASSED:**

- Created `test_script.py` with 8 test cases
- Uses `@pytest.mark.parametrize` for echo/dry_run combinations
- 100% coverage for `script.py`
- All 649 tests pass, 93% coverage
- No unnecessary `setup_logging` calls

### Phase 5: Update Documentation ✅ **COMPLETE**

**Locations:**

- `.claude/PROJECT_KNOWLEDGE.md`
- `.claude/BEST_PRACTICES.md`

**Tasks:**

1. Document `run()` new parameters
2. Document `run_script()` function
3. Document `run_uv()` enhancements
4. Add usage examples for all functions
5. Update dry-run workflow examples

**✅ COMPLETED:**

- Added "Command Execution" section to PROJECT_KNOWLEDGE.md
- Documented all three functions with parameter tables
- Added practical examples and best practices
- No updates needed for BEST_PRACTICES.md (usage is straightforward)

### Phase 6: Integration and Validation

**Tasks:**

1. Verify no circular dependencies
2. Manual testing of all features
3. Performance check (no regression)
4. Final validation: `make test` and `make lint`

## Detailed Tasks

### 1. Update `run()` Function Signature

**File:** `src/bake/ui/run/run.py`

**Changes:**

```python
def run(
    cmd: str | list[str] | tuple[str, ...],
    capture_output: bool = True,
    check: bool = True,
    cwd: Path | str | None = None,
    stream: bool = True,
    shell: bool | None = None,
    echo: bool = True,         # NEW
    dry_run: bool = False,     # NEW
    **kwargs,
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[None]:
```

**Also update all 4 overload signatures.**

**Acceptance Criteria:**

- All function signatures include new parameters
- Default values are correct (`echo=True`, `dry_run=False`)
- Type hints are correct

**Effort:** M

---

### 2. Implement Echo Logic in `run()`

**File:** `src/bake/ui/run/run.py`

**Implementation:**

```python
cmd_str = cmd if isinstance(cmd, str) else " ".join(cmd)

if echo:
    from bake.ui import console
    console.cmd(cmd_str)
```

**Placement:** After `cmd_str` construction, before dry_run check.

**Acceptance Criteria:**

- Command is displayed via `console.cmd()` when `echo=True`
- Works for both string and list/tuple commands
- Console import is lazy (inside if block)

**Effort:** S

---

### 3. Implement Dry-Run Logic in `run()`

**File:** `src/bake/ui/run/run.py`

**Implementation:**

```python
if dry_run:
    return subprocess.CompletedProcess(
        args=cmd,
        returncode=0,
        stdout="" if capture_output else None,
        stderr="" if capture_output else None,
    )
```

**Placement:** After echo logic, before existing execution logic.

**Acceptance Criteria:**

- Returns `CompletedProcess` with returncode=0
- Skips all subprocess execution
- Respects `capture_output` in return value
- Does not call `logger.debug()` for completion

**Effort:** M

---

### 4. Update `run()` Docstring

**File:** `src/bake/ui/run/run.py`

**Add to Parameters section:**

```python
echo : bool, optional
    Display command before execution using console.cmd().
    Default is True. Set to False for silent execution.
dry_run : bool, optional
    Display command without executing (dry-run mode).
    Default is False. Does NOT auto-echo; combine with echo=True
    to preview commands.

Examples
--------
>>> run("echo hello")                     # Shows and runs command
>>> run("echo hello", echo=False)         # Silent execution
>>> run("echo hello", dry_run=True)       # Silent dry-run
>>> run("echo hello", echo=True, dry_run=True)  # Show but don't run
```

**Acceptance Criteria:**

- Documentation clearly explains both parameters
- Examples show all use cases
- Explicitly notes that dry_run doesn't auto-echo

**Effort:** S

---

### 5. Create `run_script()` Function

**File:** `src/bake/ui/run/run.py`

**Implementation:**

```python
def run_script(
    title: str,
    script: str,
    capture_output: bool = True,
    check: bool = True,
    cwd: Path | str | None = None,
    stream: bool = True,
    echo: bool = True,
    dry_run: bool = False,
    **kwargs,
) -> subprocess.CompletedProcess[str]:
    """Run multi-line shell script with optional echo and dry-run.

    Displays script in a bordered box using console.script_block(),
    then executes it via run().

    Parameters
    ----------
    title : str
        Title for the script display (shown in bordered box).
    script : str
        Multi-line shell script to execute.
    capture_output : bool, optional
        Whether to capture stdout/stderr, by default True.
    check : bool, optional
        Raise exception on non-zero exit, by default True.
    cwd : Path | str | None, optional
        Working directory, by default None.
    stream : bool, optional
        Stream output to terminal in real-time, by default True.
    echo : bool, optional
        Display script in bordered box before running, by default True.
    dry_run : bool, optional
        Display script without executing, by default False.
    **kwargs
        Additional arguments passed to subprocess (not shell, which is
        always True for scripts).

    Returns
    -------
    subprocess.CompletedProcess[str]
        Completed process with captured output.

    Examples
    --------
    >>> run_script("Install", "uv pip install requests")
    >>> run_script("Setup", "pip install -r requirements.txt", dry_run=True)
    """
    if echo:
        from bake.ui import console
        console.script_block(title, script)

    if dry_run:
        return subprocess.CompletedProcess(
            args=script,
            returncode=0,
            stdout="" if capture_output else None,
            stderr="" if capture_output else None,
        )

    return run(
        script,
        capture_output=capture_output,
        check=check,
        cwd=cwd,
        stream=stream,
        echo=False,  # Already displayed via script_block
        shell=True,
        **kwargs,
    )
```

**Placement:** After `run()` function, in same file.

**Acceptance Criteria:**

- Function signature matches design
- Uses `console.script_block()` for display
- Calls `run()` with `echo=False` to avoid double display
- Always passes `shell=True` (scripts are shell commands)
- Comprehensive docstring with examples

**Effort:** M

---

### 6. Add Tests for `run()` Echo

**File:** `tests/bake/ui/run/test_run.py`

**Test cases:**

```python
class TestRunEcho:
    def test_run_echo_displays_command(self, capsys):
        run("echo test", echo=True, capture_output=False)
        captured = capsys.readouterr()
        assert "echo test" in captured.err
        assert "❯" in captured.err

    def test_run_echo_false_silent(self, capsys):
        run("echo test", echo=False, capture_output=False)
        captured = capsys.readouterr()
        # Should not show command prefix
        assert "❯" not in captured.err
```

**Acceptance Criteria:**

- Tests verify command is displayed when `echo=True`
- Tests verify silence when `echo=False`
- Tests check for `console.cmd()` output format

**Effort:** M

---

### 7. Add Tests for `run()` Dry-Run

**File:** `tests/bake/ui/run/test_run.py`

**Test cases:**

```python
class TestRunDryRun:
    def test_run_dry_run_skips_execution(self):
        result = run("echo test", dry_run=True)
        assert result.returncode == 0
        assert result.stdout == ""

    def test_run_dry_run_no_echo(self, capsys):
        run("nonexistent-command", dry_run=True, echo=False)
        captured = capsys.readouterr()
        # Should not show anything
        assert captured.err == ""

    def test_run_dry_run_with_echo(self, capsys):
        run("echo test", dry_run=True, echo=True)
        captured = capsys.readouterr()
        assert "echo test" in captured.err
```

**Acceptance Criteria:**

- Tests verify no execution occurs
- Tests verify returncode is 0
- Tests verify echo/dry_run independence

**Effort:** M

---

### 8. Add Tests for `run_script()` Basic

**File:** `tests/bake/ui/run/test_run.py` (or new file)

**Test cases:**

```python
class TestRunScript:
    def test_run_script_executes(self, capsys):
        result = run_script("Test", "echo hello")
        assert result.returncode == 0
        assert "hello" in result.stdout

    def test_run_script_displays_box(self, capsys):
        run_script("Test", "echo hello", echo=True)
        captured = capsys.readouterr()
        assert "Test" in captured.err
        assert "━" in captured.err  # box border
        assert "echo hello" in captured.err
```

**Acceptance Criteria:**

- Tests verify script execution
- Tests verify script_block display
- Tests verify proper output capture

**Effort:** M

---

### 9. Add Tests for `run_script()` Dry-Run

**File:** `tests/bake/ui/run/test_run.py`

**Test cases:**

```python
    def test_run_script_dry_run(self, capsys):
        result = run_script("Test", "echo hello", dry_run=True)
        assert result.returncode == 0
        # Should not actually execute

    def test_run_script_dry_run_with_echo(self, capsys):
        run_script("Test", "echo hello", echo=True, dry_run=True)
        captured = capsys.readouterr()
        assert "Test" in captured.err
        assert "echo hello" in captured.err
```

**Acceptance Criteria:**

- Tests verify no execution in dry-run mode
- Tests verify display still works with dry_run

**Effort:** M

---

### 10. Update `run_uv()` Function Signature

**File:** `src/bake/ui/run/uv.py`

**Changes:**

```python
def run_uv(
    cmd: list[str] | tuple[str, ...],
    capture_output: bool = True,
    check: bool = True,
    cwd: Path | str | None = None,
    stream: bool = False,
    echo: bool = True,         # NEW
    dry_run: bool = False,     # NEW
    **kwargs,
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[None]:
```

**Also update both overload signatures.**

**Acceptance Criteria:**

- Both function signatures include new parameters
- Default values are correct (`echo=True`, `dry_run=False`)
- Type hints are correct

**Effort:** M

---

### 11. Implement Echo Logic in `run_uv()`

**File:** `src/bake/ui/run/uv.py`

**Implementation:**

```python
# Build display string: "uv" + command parts (no full binary path)
display_cmd = "uv " + " ".join(cmd)

if echo:
    from bake.ui import console
    console.cmd(display_cmd)
```

**Placement:** After `uv_bin = find_uv_bin()`, before dry_run check.

**Acceptance Criteria:**

- Display shows only `"uv"` prefix, not full path like `/usr/local/bin/uv`
- Command parts are joined with spaces
- Console import is lazy (inside if block)

**Effort:** S

---

### 12. Implement Dry-Run Logic in `run_uv()`

**File:** `src/bake/ui/run/uv.py`

**Implementation:**

```python
if dry_run:
    return subprocess.CompletedProcess(
        args=cmd,
        returncode=0,
        stdout="" if capture_output else None,
        stderr="" if capture_output else None,
    )
```

**Placement:** After echo logic, before calling `run()`.

**Acceptance Criteria:**

- Returns `CompletedProcess` with returncode=0
- Skips calling `run()` entirely
- Respects `capture_output` in return value

**Effort:** S

---

### 13. Update `run_uv()` to Pass Through to `run()`

**File:** `src/bake/ui/run/uv.py`

**Changes:**

```python
# When NOT in dry_run mode, call run() with echo=False
# (echo already handled by run_uv's own echo logic)
return run(
    [uv_bin, *cmd],
    capture_output=capture_output,
    check=check,
    cwd=cwd,
    stream=stream,
    echo=False,  # Don't echo again (already displayed if needed)
    **kwargs,
)
```

**Acceptance Criteria:**

- Full uv binary path is passed to `run()`
- `echo=False` prevents double display
- All other params are passed through

**Effort:** S

---

### 14. Update `run_uv()` Docstring

**File:** `src/bake/ui/run/uv.py`

**Add to docstring:**

```python
Parameters
----------
...
echo : bool, optional
    Display command using console.cmd() with "uv" prefix
    (not full binary path). Default is True.
dry_run : bool, optional
    Display command without executing (dry-run mode).
    Default is False.

Examples
--------
>>> run_uv(["pip", "install", "requests"])
# Displays: ❯ uv pip install requests

>>> run_uv(["pip", "install", "requests"], dry_run=True)
# Displays: ❯ uv pip install requests (doesn't execute)
```

**Acceptance Criteria:**

- Documents "uv" only prefix behavior
- Examples show actual display output
- Notes independence from `run()`'s echo

**Effort:** S

---

### 15. Add Tests for `run_uv()` Echo

**File:** `tests/bake/ui/run/test_uv.py` (or create new)

**Test cases:**

```python
class TestRunUvEcho:
    def test_run_uv_echo_displays_uv_only(self, capsys):
        run_uv(["pip", "install", "requests"], echo=True)
        captured = capsys.readouterr()
        assert "uv pip install requests" in captured.err
        assert "/usr/local/bin/uv" not in captured.err
        assert "❯" in captured.err

    def test_run_uv_echo_false_silent(self, capsys):
        run_uv(["version"], echo=False)
        captured = capsys.readouterr()
        assert "❯" not in captured.err
```

**Acceptance Criteria:**

- Tests verify "uv" is displayed, not full path
- Tests verify silence when `echo=False`

**Effort:** M

---

### 16. Add Tests for `run_uv()` Dry-Run

**File:** `tests/bake/ui/run/test_uv.py`

**Test cases:**

```python
class TestRunUvDryRun:
    def test_run_uv_dry_run_skips_execution(self):
        result = run_uv(["version"], dry_run=True)
        assert result.returncode == 0
        # Should not actually execute uv

    def test_run_uv_dry_run_with_echo(self, capsys):
        run_uv(["pip", "install", "requests"], echo=True, dry_run=True)
        captured = capsys.readouterr()
        assert "uv pip install requests" in captured.err
```

**Acceptance Criteria:**

- Tests verify no execution occurs
- Tests verify echo still works with dry_run

**Effort:** M

---

### 17. Update PROJECT_KNOWLEDGE.md

**File:** `.claude/PROJECT_KNOWLEDGE.md`

**Add section:**

````markdown
### Command Execution

#### run() - Execute Commands

Run commands with optional display and dry-run:

```python
from bake.ui.run import run

# Show and run
run("uv pip install requests")

# Silent execution
run("uv pip install requests", echo=False)

# Preview without running
run("uv pip install requests", dry_run=True)

# Show preview only
run("uv pip install requests", echo=True, dry_run=True)
```
````

#### run_script() - Execute Shell Scripts

Run multi-line shell scripts with formatted display:

```python
from bake.ui.run import run_script

# Show and run script
run_script("Install", """uv pip install \\
    requests>=2.32.0 \\
    click""")

# Preview script
run_script("Install", "...", dry_run=True)
```

#### run_uv() - Execute UV Commands

Run uv commands with "uv" prefix display (not full binary path):

```python
from bake.ui.run import run_uv

# Show and run (displays "uv pip install...")
run_uv(["pip", "install", "requests"])

# Silent execution
run_uv(["pip", "install", "requests"], echo=False)

# Preview without running
run_uv(["pip", "install", "requests"], dry_run=True)
```

```

**Acceptance Criteria:**
- Clear documentation of new features
- Practical examples
- Consistent with existing doc style

**Effort:** S

---

## Risk Assessment and Mitigation

### Risk 1: Breaking Existing Tests

**Risk:** Existing tests may fail due to new default `echo=True` behavior.

**Mitigation:**
- Run full test suite after implementation
- Update tests that expect silent execution to explicitly pass `echo=False`

**Impact:** M

---

### Risk 2: Console Import Circular Dependency

**Risk:** Lazy import of `console` module may cause issues.

**Mitigation:**
- Keep import inside `if echo:` block (already planned)
- Test import in isolation
- Verify no circular dependencies

**Impact:** L

---

### Risk 3: Double Display in `run_script()`

**Risk:** Both `script_block` and `run()` might echo the same content.

**Mitigation:**
- Explicitly pass `echo=False` when calling `run()` from `run_script()`
- Add tests to verify no double display

**Impact:** M

---

### Risk 4: PTY/Color Handling with Dry-Run

**Risk:** Dry-run mode might not properly handle PTY initialization.

**Mitigation:**
- Early return before PTY code path
- Test dry-run separately from PTY logic

**Impact:** S

---

### Risk 5: Double Display in `run_uv()`

**Risk:** Both `run_uv()`'s echo and `run()`'s echo might display.

**Mitigation:**
- Pass `echo=False` to `run()` when calling from `run_uv()`
- Add tests to verify no double display

**Impact:** M

---

## Success Metrics

1. **All existing tests pass** without modification (or with minimal updates for new defaults)
2. **New test coverage** ≥ 90% for new features
3. **No performance regression** in `run()` execution path
4. **Documentation complete** with clear examples
5. **No circular dependencies** introduced

## Required Resources and Dependencies

### Dependencies
- `beautysh` package (already installed for `script_block`)
- `pytest` for testing (already in project)
- Existing `console` module

### Resource Requirements
- Development time: ~6 hours
- Testing time: ~3 hours
- Documentation time: ~1 hour
- Validation: ~1 hour (lint + test runs)

## Timeline Estimates

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| Phase 1: Update run() | Tasks 1-4 | 2 hours |
| ⚠️ **Validation: make lint & make test** | | 0.5 hours |
| Phase 2: Update run_uv() | Tasks 10-14 | 1 hour |
| ⚠️ **Validation: make lint & make test** | | 0.5 hours |
| Phase 3: Implement run_script() | Task 5 | 1.5 hours |
| Phase 4: Update Tests | Tasks 6-9, 15-16 | 3 hours |
| Phase 5: Documentation | Task 17 | 1 hour |
| Phase 6: Integration | Tests + validation | 1 hour |
| **Total** | | **10.5 hours** |

## Open Questions

1. Should `run_script()` support `shell=False` for non-shell multi-line scripts?
   - **Decision:** No, always `shell=True` (scripts are shell commands by nature)

2. Should `dry_run` return different returncodes for success/failure simulation?
   - **Decision:** No, always return 0 (dry-run is "success by definition")

3. Should we add a global "verbose mode" that sets `echo=True` everywhere?
   - **Decision:** Not in this scope, can be added later via Typer context

4. Should `run_uv()` expose all `run()` parameters (capture_output, check, etc.)?
   - **Decision:** Yes, for consistency and flexibility

5. Should `run_uv()` have a `shell` parameter?
   - **Decision:** No, always passes list to `run()` which uses `shell=False` by default for safety

## Dependencies

### Internal Dependencies
- `console.cmd()` must be working correctly
- `console.script_block()` must be working correctly
- Existing `run()` function must remain stable
- `uv.find_uv_bin()` must be working correctly

### External Dependencies
- `uv` package (already installed)
- None (all other dependencies are existing)
```
