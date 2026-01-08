# Context: Echo and Dry-Run Features for Run Module

**Last Updated:** 2026-01-02 (Phase 1-5 complete)

## Purpose

Add `echo` and `dry_run` capabilities to the `run()` function and implement `run_script()` for multi-line shell script execution with proper display formatting.

## Key Design Decisions

### 1. Echo Default: True

**Decision:** `echo=True` by default

**Rationale:**

- Safer — users always see what's being executed
- More transparent — no silent commands
- Consistent with CLI best practices (show before doing)

**Trade-off:** Noisier output, but users can opt-out with `echo=False`

### 2. Dry-Run Independence

**Decision:** `dry_run` does NOT auto-enable `echo`

**Rationale:**

- Independent control over display and execution
- Allows silent dry-runs for testing
- Allows visible dry-runs for previewing
- User explicitly combines: `run(..., echo=True, dry_run=True)`

**Behavior Matrix:**
| echo | dry_run | Result |
|-----|---------|--------|
| T | F | Show + Run |
| T | T | Show + Skip |
| F | F | Silent + Run |
| F | T | Silent + Skip |

### 3. run_script() Shell Parameter

**Decision:** `run_script()` always uses `shell=True`, no `shell` parameter exposed

**Rationale:**

- Multi-line scripts are inherently shell commands
- Simplifies API (one less parameter)
- `shell=False` doesn't make sense for multi-line scripts

### 4. Double Display Prevention

**Decision:** `run_script()` calls `run()` with `echo=False`

**Rationale:**

- `run_script()` uses `console.script_block()` for display
- Calling `run()` with `echo=True` would double-display
- Explicit `echo=False` prevents this

## Key Files

### Files to Modify

1. **src/bake/ui/run/run.py** (Main implementation)
    - Add `echo` and `dry_run` to `run()` function
    - Implement new `run_script()` function
    - Update all overload signatures
    - Update docstrings

2. **src/bake/ui/run/uv.py** (UV implementation)
    - Add `echo` and `dry_run` to `run_uv()` function
    - Implement echo showing "uv" prefix only
    - Update both overload signatures
    - Update docstrings

3. **tests/bake/ui/run/test_run.py** (Tests)
    - Add `TestRunEcho` class
    - Add `TestRunDryRun` class
    - Add `TestRunScript` class
    - Test all echo/dry_run combinations

### Files to Reference

4. **src/bake/ui/console.py** (Display functions)
    - `cmd()` — displays single command with `❯`
    - `script_block()` — displays multi-line script in box
    - Uses `beautysh` for formatting
    - Outputs to stderr

5. **src/bake/ui/run/splitter.py** (Output handling)
    - `OutputSplitter` class
    - PTY handling for color preservation
    - Not changing, but good to understand

### Documentation Files

6. **.claude/PROJECT_KNOWLEDGE.md**
    - Add command execution section
    - Document `run()` and `run_script()` usage

7. **.claude/BEST_PRACTICES.md**
    - Add best practices for echo/dry-run usage
    - Examples of when to use each mode

## Function Signatures

### Updated run()

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

### New run_script()

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
```

### Updated run_uv()

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
) -> subprocess.CompletedProcess[str]:
```

**Key difference:** `run_uv()` echo shows only `"uv"` prefix, not full binary path.

## Implementation Notes

### Import Strategy

Use lazy import for console module to avoid circular dependency:

```python
if echo:
    from bake.ui import console
    console.cmd(cmd_str)
```

### Dry-Run Return Value

```python
if dry_run:
    return subprocess.CompletedProcess(
        args=cmd,
        returncode=0,
        stdout="" if capture_output else None,
        stderr="" if capture_output else None,
    )
```

**Key points:**

- Always return `returncode=0` (dry-run is "success")
- Respect `capture_output` parameter in return value
- Skip all subprocess execution
- Skip `logger.debug()` completion log

### run_script() Internal Call

```python
return run(
    script,
    capture_output=capture_output,
    check=check,
    cwd=cwd,
    stream=stream,
    echo=False,  # Critical: prevent double display
    shell=True,  # Always True for scripts
    **kwargs,
)
```

### run_uv() Display Logic

```python
# Build display string (shows only "uv", not full path)
display_cmd = "uv " + " ".join(cmd)

if echo:
    from bake.ui import console
    console.cmd(display_cmd)

# Call run with full uv binary path
return run(
    [uv_bin, *cmd],
    capture_output=capture_output,
    check=check,
    cwd=cwd,
    stream=stream,
    echo=False,  # Critical: prevent double display
    **kwargs,
)
```

**Key points:**

- Display: `"uv pip install requests"` (clean)
- Execution: `["/usr/local/bin/uv", "pip", "install", "requests"]` (full path)
- User sees `"uv"` prefix, not the binary path

## Testing Strategy

### Test Categories

1. **Echo tests** — verify display works
2. **Dry-run tests** — verify execution is skipped
3. **Combined tests** — verify echo + dry_run independence
4. **run_script() tests** — verify script display and execution
5. **Regression tests** — ensure existing behavior works

### Test Fixtures Needed

- `capsys` for capturing output
- Mock commands for predictable output
- Complex multi-line scripts for formatting tests

## Potential Issues to Watch

### 1. Circular Imports

**Issue:** `run` module importing `console` module

**Solution:** Lazy import inside `if echo:` block

### 2. Double Display

**Issue:** `run_script()` showing script twice

**Solution:** Explicit `echo=False` when calling `run()` from `run_script()`

### 3. Test Failures from New Defaults

**Issue:** Existing tests expect `echo=False` behavior

**Solution:** Update tests to explicitly set `echo=False` where needed

### 4. PTY Initialization in Dry-Run

**Issue:** Dry-run might trigger PTY setup

**Solution:** Early return before PTY code path

## Acceptance Criteria

### Phase 1: run() Updates

- [ ] All 4 overload signatures updated
- [ ] Echo logic working with `console.cmd()`
- [ ] Dry-run returning proper `CompletedProcess`
- [ ] Docstring updated with examples

### Phase 2: run_script() Implementation

- [ ] Function signature matches spec
- [ ] Echo uses `console.script_block()`
- [ ] Dry-run works independently
- [ ] Internal `run()` call has `echo=False, shell=True`
- [ ] Comprehensive docstring

### Phase 3: Tests

- [ ] All new tests passing
- [ ] Existing tests still passing (or updated)
- [ ] Test coverage ≥ 90% for new features

### Phase 4: Documentation

- [ ] PROJECT_KNOWLEDGE.md updated
- [ ] BEST_PRACTICES.md updated (if needed)
- [ ] Examples are clear and practical

### Phase 5: run_uv() Updates

- [ ] Both overload signatures updated
- [ ] Echo shows only "uv" prefix
- [ ] Dry-run returns proper `CompletedProcess`
- [ ] Internal `run()` call has `echo=False`
- [ ] Docstring updated with display examples

### Phase 6: Integration

- [ ] No circular dependencies
- [ ] No performance regression
- [ ] Manual testing confirms behavior

## Related Code Patterns

### Console Module Pattern

The console module has a pattern for output functions:

- `success()` — formatted with emoji, stdout
- `echo()` — plain output, stdout
- `warning()` — formatted with emoji, stderr
- `error()` — formatted with emoji, stderr
- `cmd()` — command display with `❯`, stderr
- `script_block()` — boxed script display, stderr

**Key insight:** `run()` with `echo=True` should feel natural in this ecosystem.

### Existing run() Behavior

The existing `run()` function:

- Auto-detects `shell` from command type (str → True, list → False)
- Uses PTY on Unix for color preservation
- Streams output in real-time when `stream=True`
- Captures output when `capture_output=True`
- Raises `CalledProcessError` when `check=True` and returncode != 0

**Key insight:** New features should not break any existing behavior.

## Progress Tracking

Current status: **Phase 1-5 complete (83% overall progress)**

**Completed Phases:**

✅ **Phase 1: Update `run()` Function**

- Added `echo=True` and `dry_run=False` parameters (keyword-only)
- Implemented echo logic using `console.cmd()`
- Implemented dry_run logic with debug logging
- Changed from `subprocess.CalledProcessError` to `typer.Exit`
- Refactored from ~190 lines into 10 focused helper functions
- Updated all 13 existing calls to use `echo=False` for backward compatibility
- Validated: make lint ✓, make test ✓ (641 tests, 93% coverage)

✅ **Phase 2: Update `run_uv()` Function**

- Added `echo=True` and `dry_run=False` parameters (keyword-only)
- Implemented echo showing "uv" prefix only (not full binary path)
- Passes `dry_run` through to `run()` (not handled early)
- Validated: make lint ✓, make test ✓ (641 tests, 93% coverage)

✅ **Phase 3: Implement `run_script()` Function**

- Created `run_script(title, script, ...)` function with full signature
- Moved to `src/bake/ui/run/script.py` (separate file)
- No docstring (per project policy)
- Implemented echo logic using `console.script_block()`
- Implemented dry_run logic with early return and debug logging
- Calls `run()` internally with `echo=False, shell=True`
- Exported in `__init__.py`
- Validated: make lint ✓, make test ✓ (649 tests, 93% coverage)

✅ **Phase 4: Update Tests**

- Created `tests/bake/ui/run/test_script.py` with 8 test cases
- Uses `@pytest.mark.parametrize` for echo/dry_run combinations
- Tests: basic execution, echo + dry_run, capture_output=False, multi-line scripts
- No unnecessary `setup_logging` calls
- 100% coverage for `script.py`
- Validated: make lint ✓, make test ✓ (649 tests, 93% coverage)

✅ **Phase 5: Update Documentation**

- Added "Command Execution" section to `.claude/PROJECT_KNOWLEDGE.md`
- Documented `run()`, `run_script()`, `run_uv()` with examples
- Added parameter tables and best practices

**Next Steps:**

6. **Phase 6: Integration and Validation** (4 tasks)
    - Verify no circular dependencies
    - Manual testing
    - Performance check
    - Final validation

**Key Changes from Plan:**

- `run_uv()` moved to Phase 2 (was Phase 5 in original plan)
- `run_script()` moved to separate file `script.py`
- Validation steps completed after Phases 1-5
- Function refactoring completed for better readability
- All backward compatibility updates completed
- Test file simplified with parametrize and no unnecessary logging setup
