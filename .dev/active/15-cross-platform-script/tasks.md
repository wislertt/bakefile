# Tasks: Cross-Platform Multi-Line Script Support

**Last Updated:** 2025-01-12

## Phase 1: Core Implementation

### Task 1.1: Add Temp File Creation Logic

- [ ] Import required modules (`tempfile`, `os`, `sys`) in `script.py`
- [ ] Create `_create_temp_script(script: str) -> tuple[int, str]` helper
- [ ] Use `tempfile.mkstemp()` with appropriate suffix (`.bat` for Windows)
- [ ] Write script content to file with UTF-8 encoding
- [ ] Close file descriptor before returning
- [ ] Test on Windows: Verify temp file is created with correct content

### Task 1.2: Implement Windows Execution Path

- [ ] Add detection: `sys.platform == "win32" and "\n" in script`
- [ ] Create `_run_script_with_temp_file()` function
- [ ] Use `cmd.exe /c` to execute temp file
- [ ] Preserve all existing parameters (`capture_output`, `check`, `cwd`, `stream`)
- [ ] Integrate into main `run_script()` function with conditional logic
- [ ] Test on Windows: Multi-line script executes completely

### Task 1.3: Add Cleanup with Try-Finally

- [ ] Wrap temp file execution in try-finally block
- [ ] Delete temp file in finally clause
- [ ] Use `os.path.exists()` check before deletion
- [ ] Test: Temp file deleted after successful execution
- [ ] Test: Temp file deleted after failed execution

### Task 1.4: Update Function Signature (Verification Only)

- [ ] Verify existing public API works unchanged
- [ ] Verify `stream` parameter works with temp file approach
- [ ] Verify `capture_output` parameter works with temp file approach
- [ ] Verify `dry_run` still skips temp file creation
- [ ] Verify `echo` still displays script before execution

## Phase 2: Testing

### Task 2.1: Fix Failing Multi-Line Test on Windows

- [ ] Run `test_run_script_multi_line_script` on Windows
- [ ] Verify both "hello" and "world" appear in output
- [ ] Verify test passes on Unix (no regression)

### Task 2.2: Add Windows-Specific Test If Needed

- [ ] Create test for multi-line script with Windows batch syntax
- [ ] Create test for script with empty lines
- [ ] Create test for script with special characters
- [ ] Mark tests as Windows-only if needed using `@pytest.mark.skipif`

### Task 2.3: Verify Single-Line Scripts Still Work

- [ ] Run all existing single-line script tests on Windows
- [ ] Run all existing single-line script tests on Unix
- [ ] Verify no performance regression
- [ ] Verify temp file is NOT created for single-line scripts

### Task 2.4: Test Temp File Cleanup

- [ ] Verify temp file deleted after successful execution
- [ ] Verify temp file deleted after failed execution
- [ ] Test concurrent script execution (multiple scripts at once)
- [ ] Verify no temp file leaks under normal operation
- [ ] Check temp directory is clean after test suite runs

## Phase 3: Edge Cases & Robustness

### Task 3.1: Handle UTF-8 Scripts

- [ ] Create test with non-ASCII characters (é, ñ, 中文, etc.)
- [ ] Implement UTF-8 with BOM for Windows .bat files if needed
- [ ] Verify encoding works correctly on both platforms
- [ ] Document encoding requirements for users

### Task 3.2: Handle Script Execution Failures

- [ ] Test with script that has syntax errors
- [ ] Verify error messages are helpful
- [ ] Verify temp file is still cleaned up on error
- [ ] Verify error propagation works correctly

### Task 3.3: Handle Concurrent Script Executions

- [ ] Create test that runs multiple scripts simultaneously
- [ ] Verify each script gets unique temp file name
- [ ] Verify no race conditions or file conflicts
- [ ] Verify all scripts execute correctly

### Task 3.4: Add Debugging Support (Keep Temp File Option)

- [ ] Add `keep_temp_file: bool = False` parameter to `run_script()`
- [ ] Skip cleanup when `keep_temp_file=True`
- [ ] Log temp file path when kept
- [ ] Add documentation for debugging usage
- [ ] Create test for `keep_temp_file` parameter

## Progress Summary

| Phase     | Tasks        | Complete | Progress |
| --------- | ------------ | -------- | -------- |
| Phase 1   | 4 tasks      | 0/4      | 0%       |
| Phase 2   | 4 tasks      | 0/4      | 0%       |
| Phase 3   | 4 tasks      | 0/4      | 0%       |
| **Total** | **12 tasks** | **0/12** | **0%**   |

## Notes

- Start with Phase 1 to get basic functionality working
- Move to Phase 2 to ensure test coverage
- Phase 3 is for polish and edge cases (can be deferred if needed)
- Run Windows CI after each phase to catch issues early
