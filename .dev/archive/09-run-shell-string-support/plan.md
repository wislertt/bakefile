# Plan: Support String Commands with Shell in `run()` Function

**Last Updated:** 2025-01-02 (Updated with simplification: subprocess.Popen handles shell internally)

## Executive Summary

Enhance the `run()` function in `bake.ui.run` to accept **string commands** in addition to the current list/tuple format. String commands will automatically use `shell=True`, enabling powerful shell features like command chaining (`&&`), pipes (`|`), wildcards (`*`), and redirects (`>`/`<`). This improves the task runner UX by making complex command sequences more natural and concise.

**Target User Experience:**

```python
# Before (current)
run(["uv", "pip", "list"])

# After (enhanced)
run("uv pip list && uv pip install -e .")
run("ls tests/*.py | wc -l")
run("coverage report > coverage.txt")
```

---

## Current State Analysis

### Existing `run()` Function

- **Location:** `src/bake/ui/run/run.py`
- **Signature:** `cmd: list[str] | tuple[str, ...]` (list/tuple only)
- **Default behavior:** `stream=True` (PTY-based color preservation on Unix)
- **Shell support:** Available via `**kwargs` but not default
- **PTY integration:** Full color preservation via `pty.openpty()` on Unix

### Key Constraints & Requirements

1. **PTY + Shell Interaction:** PTY works with both string and list args when `shell=True`
2. **Type Safety:** Need proper type overloads for string vs list/tuple
3. **Backward Compatibility:** Must not break existing `run([...])` calls
4. **Cross-Platform:** Unix uses bash, Windows uses cmd.exe
5. **Stream Mode:** PTY color preservation must continue working

### Current Usage Analysis

- **Internal usage:** ~10 files use `run()` with list syntax
- **Test coverage:** Comprehensive tests in `tests/bake/ui/run/test_run.py`
- **User-facing:** Used in user's `bakefile.py` for task definitions

---

## Proposed Future State

### Enhanced `run()` Signature

```python
# New overload for string commands
@overload
def run(
    cmd: str,
    shell: Literal[True] = True,
    capture_output: Literal[True] = True,
    check: bool = True,
    cwd: Path | str | None = None,
    stream: bool = True,
    **kwargs,
) -> subprocess.CompletedProcess[str]: ...

# Existing overload for list/tuple (unchanged)
@overload
def run(
    cmd: list[str] | tuple[str, ...],
    shell: Literal[False] = False,
    capture_output: Literal[True] = True,
    ...
) -> subprocess.CompletedProcess[str]: ...

# Main function with type union
def run(
    cmd: str | list[str] | tuple[str, ...],
    shell: bool = False,  # Auto-detected from type
    ...
)
```

### Behavior Matrix

| Input Type        | Shell   | Use Case                 | Example                   |
| ----------------- | ------- | ------------------------ | ------------------------- |
| `str`             | `True`  | Shell features, chaining | `"cmd1 && cmd2"`          |
| `list[str]`       | `False` | Direct execution, safe   | `["cmd", "arg1", "arg2"]` |
| `tuple[str, ...]` | `False` | Direct execution, safe   | `("cmd", "arg1")`         |

### User Experience Improvements

```python
# Task chaining (common in makefiles/justfiles)
@task
def test():
    run("uv pip list && pytest -v && coverage report")

# Pipes and wildcards
@task
def count_tests():
    run("find tests -name 'test_*.py' | wc -l")

# Output redirection
@task
def save_deps():
    run("uv pip freeze > requirements.txt")

# Still works - direct execution (safer)
@task
def build():
    run(["uv", "build", "--release"])
```

---

## Implementation Phases

### Phase 1: Type System Updates (S)

**Goal:** Add type overloads for string command support

**Tasks:**

1. Add string command overload with `shell=True` default
2. Update main function signature to accept `str | list[str] | tuple[str, ...]`
3. Add type narrowing logic for shell parameter
4. Update `__init__.py` exports if needed

**Acceptance Criteria:**

- Type checkers (mypy/pyright) correctly infer `shell=True` for strings
- Type checkers correctly infer `shell=False` for lists/tuples
- No type errors in existing codebase

---

### Phase 2: Core Logic Implementation (S)

**Goal:** Implement string command handling with shell

> **Simplification (2025-01-02):** Testing confirmed that subprocess.Popen handles `shell=True` internally regardless of PTY or regular pipes. No PTY-specific or Windows-specific shell handling needed.

**Tasks:**

1. Add type detection logic at function start:
    ```python
    if isinstance(cmd, str):
        if not shell:
            shell = True  # Auto-enable shell for strings
    ```
2. Pass `shell=shell` to subprocess.Popen in both PTY and non-PTY paths
3. Update cmd_str construction for logging (string → use directly, list/tuple → join)
4. subprocess.Popen handles shell execution internally

**Acceptance Criteria:**

- String commands execute via shell correctly
- PTY color preservation works with shell strings
- Shell parameter is passed through correctly
- Logging shows correct command strings

---

### Phase 3: Documentation & Examples (S)

**Goal:** Document new functionality and provide examples

**Tasks:**

1. Update docstring with string command examples
2. Add shell-specific parameter documentation
3. Document auto-detection behavior
4. Add security warning for untrusted input

**Acceptance Criteria:**

- Docstring clearly explains string vs list usage
- Security warning is prominent
- Examples cover common use cases

---

### Phase 4: Test Coverage (M)

**Goal:** Ensure comprehensive test coverage for new functionality

**Tasks:**

1. Add tests for string command execution
2. Add tests for command chaining (`&&`)
3. Add tests for pipes (`|`)
4. Add tests for wildcards (`*`)
5. Add tests for redirects (`>`)
6. Add tests for PTY + shell color preservation
7. Add tests for shell with `capture_output=False`
8. Add Windows-specific tests (if applicable)

**Acceptance Criteria:**

- All new functionality has test coverage
- Existing tests continue to pass
- Shell features work as expected

---

### Phase 5: Backward Compatibility Verification (S)

**Goal:** Ensure no breaking changes to existing code

**Tasks:**

1. Run full test suite
2. Verify type checking passes
3. Check all internal `run()` calls still work
4. Verify bakefile samples work
5. Manual testing with real bakefiles

**Acceptance Criteria:**

- All 623+ existing tests pass
- No type errors
- Internal usage unchanged in behavior
- Bakefile samples work correctly

---

## Risk Assessment and Mitigation

### Risk 1: Shell Injection Security

**Risk Level:** Medium
**Impact:** Users could accidentally introduce shell injection vulnerabilities
**Mitigation:**

- Add prominent security warning in docstring
- Document safe usage patterns
- Provide examples of safe vs unsafe usage
- Consider adding a `safe_mode()` helper for untrusted input

### Risk 2: Type Complexity

**Risk Level:** Low
**Impact:** More complex type signatures may confuse users
**Mitigation:**

- Clear docstring with examples
- Type narrowing makes it intuitive
- IDE autocomplete shows correct options

### Risk 3: PTY + Shell Compatibility

**Risk Level:** Resolved
**Impact:** PTY may not work correctly with shell string
**Mitigation:**

- ✓ Testing confirmed subprocess.Popen handles shell=True internally
- ✓ No PTY-specific handling needed
- ✓ Works correctly on Unix (PTY) and Windows (fallback)

### Risk 4: Cross-Platform Shell Differences

**Risk Level:** Medium
**Impact:** Commands may work differently on Unix vs Windows
**Mitigation:**

- Document platform differences
- Use common shell syntax where possible
- Test on both platforms (Unix and Windows)

### Risk 5: Breaking Changes

**Risk Level:** Low
**Impact:** Existing code may behave differently
**Mitigation:**

- Default `shell=False` for list/tuple maintains backward compatibility
- String is new type, so no existing code uses it
- Comprehensive test coverage catches regressions

---

## Success Metrics

### Functional Metrics

- [ ] String commands execute correctly with shell
- [ ] Command chaining works: `cmd1 && cmd2`
- [ ] Pipes work: `cmd1 | cmd2`
- [ ] Wildcards work: `*.py`
- [ ] Redirects work: `> file.txt`
- [ ] PTY color preservation works with shell
- [ ] All existing tests pass
- [ ] Type checking passes without errors

### Quality Metrics

- [ ] New test coverage > 90% for new functionality
- [ ] No regression in existing functionality
- [ ] Documentation is clear and comprehensive
- [ ] Code follows project best practices

### UX Metrics

- [ ] String commands are simpler to write for complex cases
- [ ] Error messages are helpful
- [ ] Examples cover common use cases
- [ ] Security implications are clear

---

## Required Resources and Dependencies

### Technical Resources

- **Python version:** 3.14+ (already in use)
- **External dependencies:** None (subprocess, pty are stdlib)
- **Platform:** Unix (PTY), Windows (fallback)

### Knowledge Resources

- subprocess documentation for shell parameter
- pty module documentation
- shlex for shell escaping (if needed)

### Human Resources

- **Developer:** Implementation (estimated ~3-4 hours)
- **QA:** Testing across platforms

### Timeline Estimates

- **Phase 1 (Type System):** 30-45 minutes
- **Phase 2 (Core Logic):** 30-45 minutes (simplified - subprocess.Popen handles shell internally)
- **Phase 3 (Documentation):** 30-45 minutes
- **Phase 4 (Tests):** 1-1.5 hours
- **Phase 5 (Verification):** 30-45 minutes

**Total:** 3-4 hours (reduced from 4-6 hours due to simplified shell handling)

---

## Open Questions

1. **Should we auto-detect shell from type, or require explicit `shell=True`?**
    - **Recommendation:** Auto-detect for better UX
    - String → shell=True, List/Tuple → shell=False

2. **Should we provide a `safe_run()` helper for untrusted input?**
    - **Recommendation:** No, not needed initially
    - Can add later if use case emerges

3. **Should we support `shell=False` with string commands?**
    - **Recommendation:** No, confusing and error-prone
    - If user wants non-shell string, use list: `[cmd_string]`

4. **Should we use `shellescape` or `shlex.quote()` for strings?**
    - **Recommendation:** No, let subprocess handle it
    - Only quote if we manually construct shell commands

---

## Dependencies

This task depends on:

- Nothing (self-contained enhancement)

Blocked by:

- Nothing (ready to implement)

Blocks:

- Nothing (enhancement only)
