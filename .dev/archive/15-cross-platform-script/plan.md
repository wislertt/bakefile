# Plan: Cross-Platform Multi-Line Script Support

**Last Updated:** 2025-01-12

## Executive Summary

Implement cross-platform support for multi-line scripts in `run_script()` function. Currently, multi-line scripts work on Unix but fail on Windows because Windows `cmd.exe /c` only executes the first line of a multi-line script string.

**Goal:** Enable users to write multi-line scripts that work identically on both Unix and Windows platforms, including support for shebang lines (e.g., `#!/usr/bin/env python3`).

## Current State Analysis

### Problem Statement

**Issue 1: Multi-line scripts on Windows**

When `run_script()` is called with a multi-line script on Windows:

```python
script = """
echo hello
echo world
"""
run_script("Test", script)
```

**Unix behavior:** Both lines execute, output is `"hello\nworld\n"`
**Windows behavior:** Only first line executes, output is `"hello\n"`

**Issue 2: Shebang scripts don't work cross-platform**

When `run_script()` is called with a shebang script:

```python
script = """#!/usr/bin/env python3
print("hello from python")
"""
run_script("Test", script)
```

**Unix behavior:** Shebang is read, Python is used as interpreter, output is `"hello from python\n"`
**Windows behavior:** Shebang is ignored, fails as batch script syntax error

### Root Cause

| Platform | Shell Command         | Multi-line Handling                 | Shebang Support         |
| -------- | --------------------- | ----------------------------------- | ----------------------- |
| Unix     | `sh -c "script"`      | Newlines are command separators     | Yes (read by shell)     |
| Windows  | `cmd.exe /c "script"` | Newlines are NOT command separators | No (ignored by cmd.exe) |

Windows `cmd.exe /c` treats newlines as part of the arguments to the first command, not as separators between commands. Additionally, Windows batch files don't support shebang lines - they're treated as comments (syntax error on line starting with `#`).

### Current Implementation

**File:** `src/bake/ui/run/script.py`

```python
def run_script(title, script, ...):
    script = script.strip()
    return run(
        script,
        shell=True,  # ← Problem: different behavior on Windows
        ...
    )
```

### Test Failure

**File:** `tests/bake/ui/run/test_script.py:53`

```python
def test_run_script_multi_line_script():
    script = """
echo hello
echo world
"""
    result = run_script("Multi-line", script)
    assert "world" in result.stdout  # ← FAILS on Windows
```

## Proposed Future State

### Solution: Temp File Approach with Shebang Support

Create a temporary script file and execute it with the appropriate interpreter. Parse shebang lines to use the correct interpreter.

**Flow:**

```
Multi-line script → Create temp file → Parse for shebang → Execute → Delete temp file
                        ↓
                 If shebang: Use that interpreter
                 If no shebang: Use default shell
```

**Platform-specific execution:**

- **Windows with shebang:** Use interpreter from shebang (e.g., `python script.bat`)
- **Windows without shebang:** `cmd.exe /c temp_script.bat`
- **Unix:** Use shebang if present, otherwise `sh temp_script.sh`

**Shebang examples:**

```python
#!/usr/bin/env python3     # Use python3 (resolved via PATH)
#!/usr/bin/python3          # Use python3 directly
#!/bin/bash                # Use bash
# (no shebang)             # Use default shell
```

### Key Design Decisions

1. **Only use temp file for Windows + multi-line scripts**
    - Single-line scripts work fine on both platforms
    - Avoids unnecessary file I/O for simple cases
    - Unix multi-line scripts also work fine (could extend later if needed)

2. **Parse and respect shebang lines**
    - Read first line of script after stripping
    - If starts with `#!`, extract and resolve interpreter
    - Use that interpreter directly (bypasses shell)
    - Makes scripts truly portable

3. **File extensions:**
    - Windows: `.bat` (even for Python/other scripts - cmd.exe handles this)
    - Unix: `.sh` (if we extend to Unix later)

4. **Cleanup guarantee:**
    - Use try-finally or context manager
    - Ensure temp file deletion even if execution fails

5. **Preserve existing behavior:**
    - All existing parameters (`stream`, `capture_output`, `echo`, `dry_run`) continue to work
    - Only the **command execution** changes, not the **interface**

6. **Interpreter resolution:**
    - For `/usr/bin/env XXX`: Find `XXX` in PATH
    - For direct paths: Use as-is
    - For Windows: Handle both Unix-style and Windows-style paths

## Implementation Phases

### Phase 1: Core Implementation

**Goal:** Make multi-line scripts work on Windows with shebang support

| Task | Description                                   | Effort |
| ---- | --------------------------------------------- | ------ |
| 1.1  | Add temp file creation logic                  | M      |
| 1.2  | Add shebang parsing function                  | M      |
| 1.3  | Add interpreter resolution logic              | M      |
| 1.4  | Implement Windows execution path with shebang | M      |
| 1.5  | Add cleanup with try-finally                  | S      |
| 1.6  | Update function signature if needed           | S      |

### Phase 2: Testing

**Goal:** Verify cross-platform behavior

| Task | Description                            | Effort |
| ---- | -------------------------------------- | ------ |
| 2.1  | Fix failing multi-line test on Windows | S      |
| 2.2  | Add shebang test (Python script)       | M      |
| 2.3  | Add shebang test (other interpreters)  | M      |
| 2.4  | Verify single-line scripts still work  | S      |
| 2.5  | Test temp file cleanup                 | M      |

### Phase 3: Edge Cases & Robustness

**Goal:** Handle real-world scenarios

| Task | Description                                   | Effort |
| ---- | --------------------------------------------- | ------ |
| 3.1  | Handle UTF-8 scripts                          | M      |
| 3.2  | Handle script execution failures              | S      |
| 3.3  | Handle concurrent script executions           | S      |
| 3.4  | Add debugging support (keep temp file option) | L      |
| 3.5  | Handle interpreter not found                  | M      |

## Detailed Tasks

### Phase 1: Core Implementation

#### Task 1.1: Add Temp File Creation Logic

**Effort:** M | **Priority:** P0

**Acceptance Criteria:**

- Function to create temp file with appropriate extension
- Write script content to file
- Return file path for execution

**Implementation Sketch:**

```python
import tempfile
import os

def _create_temp_script(script: str) -> tuple[int, str]:
    """Create temp script file, return (fd, path)."""
    suffix = ".bat" if sys.platform == "win32" else ".sh"
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.write(fd, script.encode("utf-8"))
    os.close(fd)
    return fd, path
```

#### Task 1.2: Add Shebang Parsing Function

**Effort:** M | **Priority:** P0

**Acceptance Criteria:**

- Parse first line of script for shebang
- Return interpreter path or None
- Handle both `/usr/bin/env XXX` and direct paths

**Implementation Sketch:**

```python
import shutil

def _parse_shebang(script: str) -> str | None:
    """Parse shebang line, return interpreter path or None."""
    lines = script.strip().splitlines()
    if not lines or not lines[0].startswith('#!'):
        return None

    shebang = lines[0][2:].strip()  # Remove "#!"

    # Handle /usr/bin/env XXX
    if shebang.startswith('/usr/bin/env/'):
        interpreter = shebang.split()[-1]  # Get "XXX" from "/usr/bin/env XXX"
        return shutil.which(interpreter)

    # Direct path
    return shebang
```

#### Task 1.3: Add Interpreter Resolution Logic

**Effort:** M | **Priority:** P0

**Acceptance Criteria:**

- Resolve interpreter path from shebang
- Handle `/usr/bin/env XXX` format
- Find interpreter in PATH on Windows
- Return `None` if interpreter not found

**Implementation Sketch:**

```python
def _resolve_interpreter(interpreter: str) -> str | None:
    """Resolve interpreter path, handling cross-platform differences."""
    # If it's an absolute path, use as-is
    if os.path.isabs(interpreter):
        return interpreter if os.path.exists(interpreter) else None

    # Search in PATH
    return shutil.which(interpreter)
```

#### Task 1.4: Implement Windows Execution Path with Shebang

**Effort:** M | **Priority:** P0

**Acceptance Criteria:**

- Detect multi-line script on Windows
- Check for shebang and use interpreter if present
- Fall back to cmd.exe if no shebang
- Clean up temp file

**Implementation Location:** `src/bake/ui/run/script.py`

**Code Changes:**

```python
def _run_script_with_temp_file(title, script, capture_output, check, cwd, stream, **kwargs):
    fd, path = _create_temp_script(script)
    try:
        # Check for shebang
        interpreter = _parse_shebang(script)

        if interpreter:
            # Use interpreter from shebang
            return run([interpreter, path],
                       capture_output=capture_output, check=check,
                       cwd=cwd, stream=stream, echo=False, **kwargs)
        else:
            # Use default shell
            if sys.platform == "win32":
                return run(["cmd.exe", "/c", path],
                           capture_output=capture_output, check=check,
                           cwd=cwd, stream=stream, echo=False, **kwargs)
            else:
                return run(["sh", path],
                           capture_output=capture_output, check=check,
                           cwd=cwd, stream=stream, echo=False, **kwargs)
    finally:
        if os.path.exists(path):
            os.unlink(path)
```

**Main function integration:**

```python
def run_script(title, script, ...):
    script = script.strip()

    if echo:
        console.script_block(title, script)

    if dry_run:
        # ... existing dry_run logic ...

    # NEW: Windows multi-line script handling
    if sys.platform == "win32" and "\n" in script:
        return _run_script_with_temp_file(
            title, script, capture_output, check, cwd, stream, **kwargs
        )

    # EXISTING: Direct execution
    return run(script, shell=True, ...)
```

#### Task 1.5: Add Cleanup with Try-Finally

**Effort:** S | **Priority:** P0

**Acceptance Criteria:**

- Temp file deleted after execution (success or failure)
- No temp file leaks

**Implementation:**
(See Task 1.4 - try-finally already included)

#### Task 1.6: Update Function Signature (If Needed)

**Effort:** S | **Priority:** P1

**Acceptance Criteria:**

- No breaking changes to public API
- All existing parameters work correctly

**Note:** Current signature should work. This task is verification-only.

### Phase 2: Testing

#### Task 2.1: Fix Failing Multi-Line Test on Windows

**Effort:** S | **Priority:** P0

**File:** `tests/bake/ui/run/test_script.py:53`

**Acceptance Criteria:**

- `test_run_script_multi_line_script` passes on Windows
- Both "hello" and "world" appear in output

#### Task 2.2: Add Shebang Test (Python Script)

**Effort:** M | **Priority:** P0

**Acceptance Criteria:**

- Test Python script with `#!/usr/bin/env python3` shebang
- Script executes with Python interpreter on both platforms
- Output contains expected Python script output

**Test Sketch:**

```python
def test_run_script_with_python_shebang():
    script = """#!/usr/bin/env python3
import sys
print("hello from python")
sys.exit(0)
"""
    result = run_script("Python Test", script)
    assert result.returncode == 0
    assert "hello from python" in result.stdout
```

#### Task 2.3: Add Shebang Test (Other Interpreters)

**Effort:** M | **Priority:** P1

**Acceptance Criteria:**

- Test with bash shebang (`#!/bin/bash` or `#!/usr/bin/env bash`)
- Test with direct path shebang (`#!/usr/bin/python3`)
- Verify correct interpreter is used

**Note:** Skip on platforms where interpreter not available.

#### Task 2.4: Verify Single-Line Scripts Still Work

**Effort:** S | **Priority:** P0

**Acceptance Criteria:**

- All existing single-line tests pass
- No performance regression for simple scripts
- Temp file NOT created for single-line scripts

#### Task 2.5: Test Temp File Cleanup

**Effort:** M | **Priority:** P1

**Acceptance Criteria:**

- Temp files deleted after successful execution
- Temp files deleted after failed execution
- No temp file leaks in concurrent execution

### Phase 3: Edge Cases & Robustness

#### Task 3.1: Handle UTF-8 Scripts

**Effort:** M | **Priority:** P1

**Acceptance Criteria:**

- Scripts with non-ASCII characters work correctly
- Proper encoding on both platforms

**Implementation Detail:**

- Windows batch files may need UTF-8 with BOM
- Test with various Unicode characters

#### Task 3.2: Handle Script Execution Failures

**Effort:** S | **Priority:** P1

**Acceptance Criteria:**

- Script errors propagate correctly
- Temp file still cleaned up on error
- Error messages are helpful

#### Task 3.3: Handle Concurrent Script Executions

**Effort:** S | **Priority:** P2

**Acceptance Criteria:**

- Multiple scripts can run simultaneously
- Each gets unique temp file name
- No race conditions or file conflicts

**Note:** `tempfile.mkstemp()` already handles this.

#### Task 3.4: Add Debugging Support (Keep Temp File Option)

**Effort:** L | **Priority:** P3

**Acceptance Criteria:**

- Optional parameter to keep temp file for debugging
- Useful for troubleshooting script issues

**Implementation Sketch:**

```python
def run_script(title, script, *, keep_temp_file: bool = False, ...):
    if not keep_temp_file:
        # Delete in finally
```

#### Task 3.5: Handle Interpreter Not Found

**Effort:** M | **Priority:** P1

**Acceptance Criteria:**

- Graceful error when shebang interpreter not found
- Clear error message indicating which interpreter was missing
- Fall back to shell execution or fail gracefully

**Implementation Sketch:**

```python
interpreter = _parse_shebang(script)
if interpreter:
    resolved = _resolve_interpreter(interpreter)
    if not resolved:
        logger.warning(f"Shebang interpreter '{interpreter}' not found in PATH")
        # Fall back to shell execution or raise error
        # For now: fall back to shell
```

**Test cases:**

- Script with `#!/usr/bin/env nonexistent`
- Script with interpreter not in PATH
- Verify helpful error message

## Risk Assessment

### High Risks

| Risk                            | Impact | Mitigation                                           |
| ------------------------------- | ------ | ---------------------------------------------------- |
| **Temp file cleanup fails**     | High   | Use try-finally, log warnings on failure             |
| **Path permissions on Windows** | Medium | Use `tempfile.gettempdir()` which should be writable |
| **Encoding issues**             | Medium | Use UTF-8 with BOM for Windows .bat files            |
| **Interpreter not found**       | Medium | Graceful fallback or clear error message             |

### Medium Risks

| Risk                               | Impact | Mitigation                             |
| ---------------------------------- | ------ | -------------------------------------- |
| **Shebang parsing edge cases**     | Medium | Comprehensive test coverage            |
| **Performance overhead**           | Low    | Only for multi-line scripts on Windows |
| **Antivirus interference**         | Low    | Use standard temp directory            |
| **Concurrent execution conflicts** | Low    | `mkstemp()` guarantees unique names    |

## Success Metrics

### Functional

- [ ] Multi-line scripts execute completely on Windows
- [ ] Shebang scripts work on both platforms (Python, bash, etc.)
- [ ] All existing tests pass on both platforms
- [ ] No regression in single-line script performance

### Quality

- [ ] Zero temp file leaks in normal operation
- [ ] Clean error messages when script execution fails
- [ ] Clear error when shebang interpreter not found
- [ ] Cross-platform test coverage > 80%

### Performance

- [ ] Temp file overhead < 10ms per script
- [ ] No perceptible delay for users

## Required Resources and Dependencies

### Internal

- Python standard library (`tempfile`, `os`, `sys`, `shutil`)
- Existing `run()` function in `src/bake/ui/run/run.py`

### External

- None (pure Python solution)

### Testing

- Windows CI environment (GitHub Actions)
- Unix CI environment (already exists)
- Test interpreters: Python 3, bash (if available)

## Timeline Estimate

| Phase                        | Estimate       |
| ---------------------------- | -------------- |
| Phase 1: Core Implementation | 3-4 hours      |
| Phase 2: Testing             | 2-3 hours      |
| Phase 3: Edge Cases          | 2-3 hours      |
| **Total**                    | **7-10 hours** |

**Note:** Timeline increased from 5-8 hours to 7-10 hours due to added shebang support complexity.

## Open Questions

1. **Should we support multi-line scripts on Unix with temp files too?**
    - Current: Unix works fine without temp files
    - Future consideration for consistency
    - **Answered for now:** No, only Windows multi-line scripts need temp files

2. **What shebang formats should we support?**
    - `/usr/bin/env XXX` - Yes (resolved via PATH)
    - Direct paths like `/usr/bin/python3` - Yes (use as-is)
    - Relative paths like `./python` - Consider adding
    - Windows paths like `C:\Python39\python.exe` - Consider adding

3. **Should we add a `keep_temp_file` parameter for debugging?**
    - Low priority, can be added later if needed

4. **Should we support PowerShell instead of cmd.exe?**
    - PowerShell not always available (older Windows)
    - cmd.exe is more universal

5. **What about `.bat` file syntax limitations?**
    - Variables: `set VAR=value`
    - Conditionals: `if ... else ...`
    - Loops: `for ... do ...`
    - Document in user guide
    - **With shebang support, users can use Python/other interpreters instead**

6. **Should we support both `.bat` and script extensions on Windows?**
    - For Python scripts with shebang, we use `.bat` but execute with Python
    - File extension doesn't matter when using shebang approach
    - **Answered:** Keep using `.bat` for all temp files on Windows
