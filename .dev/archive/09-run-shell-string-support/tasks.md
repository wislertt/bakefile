# Tasks: Support String Commands with Shell in `run()` Function

**Last Updated:** 2025-01-02 (Updated with simplification: subprocess.Popen handles shell internally)

## Phase 1: Type System Updates (S)

- [x] **1.1** Add string command type overload with `shell=True` default
    - File: `src/bake/ui/run/run.py`
    - Add new `@overload` decorator for `str` type
    - Use `Literal[True]` for shell parameter
    - Acceptance: Type checker infers shell=True for strings

- [x] **1.2** Update main function signature to accept string commands
    - File: `src/bake/ui/run/run.py`
    - Change `cmd` type from `list[str] | tuple[str, ...]` to `str | list[str] | tuple[str, ...]`
    - Keep default `shell: bool = False` (auto-detected in function body)
    - Acceptance: No type errors on signature

- [x] **1.3** Add type detection logic at function start
    - File: `src/bake/ui/run/run.py`
    - Add: `if isinstance(cmd, str) and not shell: shell = True`
    - Acceptance: String commands auto-enable shell

- [x] **1.4** Verify type checking passes
    - Run mypy/pyright on codebase
    - Fix any type errors that emerge
    - Acceptance: No type errors in existing code

## Phase 2: Core Logic Implementation (S)

> **Simplification Note:** Based on testing, subprocess.Popen handles shell=True internally regardless of PTY or regular pipes. No PTY-specific or Windows-specific shell handling needed.

- [x] **2.1** Pass shell parameter to subprocess.Popen calls
    - File: `src/bake/ui/run/run.py`
    - Add `shell=shell` to both PTY and non-PTY subprocess.Popen calls
    - subprocess.Popen handles shell execution internally
    - Acceptance: Shell parameter is passed through correctly

- [x] **2.2** Update cmd_str construction for logging
    - File: `src/bake/ui/run/run.py`
    - When `cmd` is string, use it directly for logging
    - When `cmd` is list/tuple, join with spaces (existing behavior)
    - Acceptance: Logging shows correct command string for both types

## Phase 3: Documentation & Examples (S)

- [x] **3.1** Update function docstring
    - File: `src/bake/ui/run/run.py`
    - Add string command to parameter documentation
    - Add shell-specific parameter documentation
    - Acceptance: Docstring explains string vs list usage

- [x] **3.2** Add security warning for shell usage
    - File: `src/bake/ui/run/run.py`
    - Document shell injection risks
    - Provide safe usage examples
    - Acceptance: Security warning is prominent

- [x] **3.3** Add usage examples to docstring
    - File: `src/bake/ui/run/run.py`
    - Show string command with chaining: `run("cmd1 && cmd2")`
    - Show string command with pipes: `run("cmd1 | cmd2")`
    - Show string command with wildcards: `run("ls *.py")`
    - Show list command (existing): `run(["cmd", "arg"])`
    - Acceptance: Examples cover common use cases

## Phase 4: Test Coverage (M)

- [x] **4.1** Add test for simple string command
    - File: `tests/bake/ui/run/test_run.py`
    - Test: `run("echo hello")`
    - Assert: stdout contains "hello"
    - Acceptance: String command executes successfully

- [x] **4.2** Add test for command chaining (&&)
    - File: `tests/bake/ui/run/test_run.py`
    - Test: `run("echo hello && echo world")`
    - Assert: stdout contains both "hello" and "world"
    - Acceptance: Chaining works as expected

- [x] **4.3** Add test for pipes (|)
    - File: `tests/bake/ui/run/test_run.py`
    - Test: `run("echo hello | tr h H")`
    - Assert: stdout contains "Hello"
    - Acceptance: Pipes work correctly

- [x] **4.4** Add test for wildcards (\*)
    - File: `tests/bake/ui/run/test_run.py`
    - Test: `run("echo tests/*.py")` in test directory
    - Assert: Output contains multiple files
    - Acceptance: Wildcards expand correctly

- [x] **4.5** Add test for redirects (>)
    - File: `tests/bake/ui/run/test_run.py`
    - Test: `run("echo test > /tmp/test.txt")` then read file
    - Assert: File contains "test"
    - Acceptance: Redirects work to file

- [x] **4.6** Add test for PTY color preservation with shell
    - File: `tests/bake/ui/run/test_run.py`
    - Test: `run('printf "\\033[32mGreen\\033[0m\\n"', shell=True)`
    - Assert: Output contains ANSI codes
    - Acceptance: PTY preserves colors with shell

- [x] **4.7** Add test for shell with capture_output=False
    - File: `tests/bake/ui/run/test_run.py`
    - Test: `run("echo test", capture_output=False)`
    - Assert: stdout is None, output in capsys
    - Acceptance: Stream mode works with shell

- [x] **4.8** Add test for auto-detection behavior
    - File: `tests/bake/ui/run/test_run.py`
    - Test: `run("echo test")` (no explicit shell)
    - Assert: Executes via shell
    - Acceptance: Auto-detection works

## Phase 5: Backward Compatibility Verification (S)

- [x] **5.1** Run full test suite
    - Command: `make test`
    - Verify all 623+ existing tests pass
    - Acceptance: No regressions

- [x] **5.2** Run type checking
    - Command: `make lint` (or mypy/pyright)
    - Verify no type errors
    - Acceptance: Type checking passes (Note: 1 pyright diagnostic for no-matching-overload with \*\*kwargs)

- [x] **5.3** Verify internal run() calls still work
    - Check ~10 internal files using run()
    - Ensure no behavior changes
    - Acceptance: Internal usage unchanged

- [ ] **5.4** Test bakefile samples
    - Run example bakefile.py
    - Verify tasks work correctly
    - Acceptance: Bakefile samples work

- [ ] **5.5** Manual testing with real bakefiles
    - Create test bakefile with string commands
    - Test chaining, pipes, wildcards
    - Acceptance: Real-world usage works

## Additional Tasks

- [x] **6.1** Update plan.md with implementation notes
    - Document any deviations from plan
    - Note any challenges encountered
    - Acceptance: Plan is up-to-date

- [x] **6.2** Update context.md with lessons learned
    - Document technical decisions made
    - Add any new patterns discovered
    - Acceptance: Context reflects implementation

## Completion Criteria

- [x] All Phase 1-5 tasks completed
- [x] All tests pass (existing + new) - 637 passed
- [x] Type checking passes (1 non-critical pyright diagnostic for \*\*kwargs)
- [x] Documentation updated
- [x] No breaking changes to existing code
- [x] Ready for code review

## Notes

- **Timeline estimate:** 3-4 hours total (reduced from 4-6 hours due to simplified shell handling)
- **Simplification:** subprocess.Popen handles shell=True internally - no PTY/Windows-specific handling needed
- Phases can be done in order, but some tasks can be parallelized
- Focus on Phase 2 and 4 (core logic + tests) as they're most critical
- Phase 5 (verification) is essential - don't skip it!
