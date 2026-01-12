# Context: Cross-Platform Multi-Line Script Support

**Last Updated:** 2025-01-12

## Problem Summary

**Issue 1: Multi-line scripts on Windows**
Multi-line scripts in `run_script()` work on Unix but fail on Windows. Only the first line executes on Windows because `cmd.exe /c` doesn't treat newlines as command separators.

**Issue 2: Shebang scripts don't work cross-platform**
Scripts with shebang lines (e.g., `#!/usr/bin/env python3`) work on Unix but fail on Windows because `cmd.exe` ignores shebangs and treats lines starting with `#` as syntax errors in batch files.

## Key Files

### Implementation Files

| File                               | Role                   | Changes Needed                     |
| ---------------------------------- | ---------------------- | ---------------------------------- |
| `src/bake/ui/run/script.py`        | Core implementation    | Add temp file logic                |
| `src/bake/ui/run/run.py`           | Used by `run_script()` | No changes needed                  |
| `tests/bake/ui/run/test_script.py` | Test file              | Multi-line test failing on Windows |

### Current Implementation

**`src/bake/ui/run/script.py`:**

```python
def run_script(title, script, ...):
    script = script.strip()
    if echo:
        console.script_block(title, script)
    if dry_run:
        return subprocess.CompletedProcess(...)
    return run(script, shell=True, ...)  # ← Problem here
```

**Issue:** `shell=True` behaves differently on Windows vs Unix for multi-line scripts.

### Test Failure

**`tests/bake/ui/run/test_script.py:53-63`:**

```python
def test_run_script_multi_line_script():
    script = """
echo hello
echo world
"""
    result = run_script("Multi-line", script)
    assert "world" in result.stdout  # FAILS on Windows
```

**Error on Windows:**

```
AssertionError: assert 'world' in 'hello\n'
Only "hello" in stdout, "world" is missing
```

## Technical Decisions

### Chosen Approach: Temp File with Shebang Parsing

**Why temp file?**

1. Standard solution for cross-platform script execution
2. Reliable - well-understood pattern
3. Works with any shell features (variables, loops, conditionals)
4. Easy to debug (can inspect temp file)

**Why only for Windows?**

1. Unix multi-line scripts already work with `shell=True`
2. Avoids unnecessary file I/O for Unix users
3. Single-line scripts work fine on both platforms
4. Keeps the change minimal

**Why shebang support?**

1. Makes scripts truly portable across platforms
2. Users can write Python scripts that work everywhere
3. Avoids Windows batch file limitations (variables, conditionals)
4. Enables use of any interpreter (Python, bash, etc.)

**Alternative approaches considered:**

- Command separators (`&` on Windows) - Too limited, breaks complex scripts
- PowerShell - Not universally available
- Accept limitation - Rejected for user experience reasons

### Execution Flow

```
Multi-line script on Windows:

1. Strip whitespace from script
2. Check: Windows AND has newlines?
3. Yes → Create temp .bat file
4. Write script to temp file
5. Parse for shebang (#!)
   - If shebang: Resolve interpreter (e.g., python3)
   - Execute: interpreter temp_file.bat
   - If no shebang: Execute: cmd.exe /c temp_file.bat
6. Delete temp file (try-finally)
```

### Dependencies

**Internal:**

- `tempfile` module (Python stdlib)
- `os` module (Python stdlib)
- `sys` module (Python stdlib)
- `shutil` module (Python stdlib) - for `which()` to resolve interpreters
- Existing `run()` function

**External:**

- None required

## Platform-Specific Behavior

### Unix (Current - No Change)

```python
run_script("Test", """
echo hello
echo world
""")
# Executes: sh -c "echo hello\necho world"
# Output: "hello\nworld\n"
```

### Windows (After Fix)

**Without shebang (batch script):**

```python
run_script("Test", """
echo hello
echo world
""")
# Creates: C:\Users\...\tmpXYZ.bat
# Executes: cmd.exe /c C:\Users\...\tmpXYZ.bat
# Output: "hello\nworld\n"
```

**With shebang (Python script):**

```python
run_script("Test", """#!/usr/bin/env python3
print("hello from python")
""")
# Creates: C:\Users\...\tmpXYZ.bat
# Parses shebang: python3
# Executes: python3 C:\Users\...\tmpXYZ.bat
# Output: "hello from python\n"
```

## Related Issues

### Also Fixed During This Session

1. **Windows test failures in `test_run.py`:**
    - `test_run_string_command_redirects` - Trailing space in Windows echo
    - `test_run_command_capture_output_false` - capsys capture issue
    - `test_run_string_command_with_explicit_shell_false` - Platform difference
    - `test_run_stream_preserves_colors_with_pty` - bash not available

2. **Windows reinvocation crash:**
    - `os.execve()` doesn't work on Windows (0xC0000005 access violation)
    - Changed to `subprocess.run()` + `SystemExit`

3. **Path separator issues:**
    - Multiple tests failed due to backslash vs forward slash
    - Fixed by using `Path` objects for comparison

## Implementation Notes

### Files to Create (New)

**Helper functions in `script.py`:**

```python
def _parse_shebang(script: str) -> str | None:
    """Parse shebang line, return interpreter path or None."""

def _resolve_interpreter(interpreter: str) -> str | None:
    """Resolve interpreter path, handling cross-platform differences."""

def _run_script_with_temp_file(
    title: str,
    script: str,
    capture_output: bool,
    check: bool,
    cwd: Path | str | None,
    stream: bool,
    **kwargs,
) -> subprocess.CompletedProcess:
    """Run multi-line script using temp file on Windows with shebang support."""
```

### Files to Modify

1. **`src/bake/ui/run/script.py`**
    - Add import: `import sys`, `import tempfile`, `import os`, `import shutil`
    - Add `_parse_shebang()` function
    - Add `_resolve_interpreter()` function
    - Add `_run_script_with_temp_file()` function
    - Modify `run_script()` to detect Windows + multi-line case

2. **`tests/bake/ui/run/test_script.py`**
    - Mark `test_run_script_multi_line_script` as passing on Windows
    - Add test for Python shebang scripts
    - May add additional Windows-specific tests

### Files NOT to Modify

- `src/bake/ui/run/run.py` - No changes needed
- Other test files - Not affected

## Acceptance Criteria Summary

### Must Have (P0)

- [ ] Multi-line scripts execute completely on Windows
- [ ] Shebang scripts (e.g., `#!/usr/bin/env python3`) work on both platforms
- [ ] All existing tests pass on both platforms
- [ ] Temp files cleaned up (success or failure)
- [ ] No breaking changes to public API

### Should Have (P1)

- [ ] UTF-8 character support in scripts
- [ ] Helpful error messages on failure
- [ ] Clear error when shebang interpreter not found
- [ ] Cross-platform test coverage

### Could Have (P2/P3)

- [ ] `keep_temp_file` parameter for debugging
- [ ] Performance optimization
- [ - Extended Unix support with temp files

## Risks & Mitigations

### Risk: Temp File Cleanup Failure

**Mitigation:** Use try-finally, log but don't fail if cleanup fails

### Risk: Encoding Issues

**Mitigation:** Use UTF-8 with BOM for Windows .bat files

### Risk: Permission Denied

**Mitigation:** Use `tempfile.gettempdir()` which should always be writable

## Testing Strategy

### Unit Tests

- Single-line scripts (both platforms)
- Multi-line scripts on Windows (new behavior)
- Multi-line scripts on Unix (existing behavior)
- Shebang scripts (Python, bash, other interpreters)
- Empty scripts
- Scripts with special characters

### Integration Tests

- Scripts that set variables
- Scripts with conditionals
- Scripts with error handling
- Scripts with shebang interpreters
- Concurrent script execution

### Manual Testing

- Run bakefile.py with multi-line `run_script()` on Windows
- Run bakefile.py with shebang scripts on both platforms
- Verify temp file cleanup
- Verify output correctness
- Test interpreter resolution for various shebang formats

## Next Steps

1. Implement Phase 1 (Core Implementation) including shebang parsing
2. Run tests on Windows CI
3. Fix any issues found
4. Implement Phase 2 (Testing) with shebang test cases
5. Implement Phase 3 (Edge Cases) - if time permits
