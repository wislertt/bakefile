# Context: Support String Commands with Shell in `run()` Function

**Last Updated:** 2025-01-02 (Updated with simplification: subprocess.Popen handles shell internally)

## Key Files

### Core Implementation Files

| File                          | Purpose                         | Status             |
| ----------------------------- | ------------------------------- | ------------------ |
| `src/bake/ui/run/run.py`      | Main `run()` function to modify | Needs modification |
| `src/bake/ui/run/__init__.py` | Exports for run module          | May need updates   |
| `src/bake/ui/run/splitter.py` | OutputSplitter for PTY handling | Reference only     |

### Test Files

| File                                       | Purpose                   | Status                 |
| ------------------------------------------ | ------------------------- | ---------------------- |
| `tests/bake/ui/run/test_run.py`            | Main test suite for run() | Needs new tests        |
| `tests/bake/cli/bake/test_reinvocation.py` | Integration test example  | Reference for patterns |

### Documentation Files

| File                | Purpose               | Status            |
| ------------------- | --------------------- | ----------------- |
| `README.md`         | Project documentation | May need examples |
| `.claude/CLAUDE.md` | Project instructions  | Reference         |

## Key Decisions

### Decision 1: Auto-Detect Shell from Command Type

**Date:** 2025-01-02
**Rationale:** Better UX - users don't need to remember to set `shell=True` for strings
**Implementation:**

```python
def run(cmd: str | list[str] | tuple[str, ...], shell: bool = False, ...):
    if isinstance(cmd, str) and not shell:
        shell = True  # Auto-enable for strings
```

### Decision 2: Type Overloads for Type Safety

**Date:** 2025-01-02
**Rationale:** Type checkers should infer correct shell value from command type
**Implementation:**

- `str` → `shell: Literal[True] = True` (auto-enabled)
- `list[str] | tuple[str, ...]` → `shell: Literal[False] = False` (current behavior)

### Decision 3: Backward Compatibility

**Date:** 2025-01-02
**Rationale:** No breaking changes to existing code
**Implementation:**

- Default `shell=False` for list/tuple (current behavior)
- String is new type, so no existing code uses it
- All existing tests must pass

## Technical Constraints

### PTY + Shell Interaction

- **Issue:** PTY works with both string and list args when `shell=True`
- **Solution:** subprocess.Popen handles this internally
- **Status:** ✓ Confirmed via testing (2025-01-02)
- **Simplification:** No PTY-specific or Windows-specific shell handling needed
- **Reference:** `src/bake/ui/run/run.py:88-103` (PTY implementation)

### Type System

- **Requirement:** Proper type narrowing for shell parameter
- **Tools:** mypy, pyright
- **Pattern:** Use `@overload` with `Literal` types

### Cross-Platform

- **Unix:** Uses bash with PTY for color preservation
- **Windows:** Uses cmd.exe, no PTY (fallback to PIPE)
- **Implementation:** Use `sys.platform != "win32"` check (existing pattern)

## Dependencies

### External Dependencies

- **subprocess** (stdlib) - Core subprocess execution
- **pty** (stdlib, Unix only) - Pseudo-terminal for color preservation
- **typing** (stdlib) - Type hints and overloads

### Internal Dependencies

- `bake.ui.run.splitter.OutputSplitter` - Output streaming with PTY support
- `bake.ui.logger` - Logging utilities

### Blockers

- None - ready to implement

## Reference Code Patterns

### Current run() Signature

```python
# File: src/bake/ui/run/run.py:18-47
@overload
def run(
    cmd: list[str] | tuple[str, ...],
    capture_output: Literal[True] = True,
    check: bool = True,
    cwd: Path | str | None = None,
    stream: bool = True,
    **kwargs,
) -> subprocess.CompletedProcess[str]: ...
```

### PTY Usage Pattern

```python
# File: src/bake/ui/run/run.py:88-103
if use_pty:
    stdout_fd, slave_fd = pty.openpty()
    env = os.environ.copy()
    env.setdefault("FORCE_COLOR", "1")
    env.setdefault("CLICOLOR_FORCE", "1")
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=slave_fd,
        stderr=subprocess.PIPE if capture_output else None,
        env=env,
        **kwargs,
    )
```

### Test Pattern

```python
# File: tests/bake/ui/run/test_run.py:18-30
def test_run_simple_command(capsys: pytest.CaptureFixture[str]) -> None:
    setup_logging(level_per_module={"": logging.DEBUG}, is_pretty_log=False)
    _ = capsys.readouterr()
    result = run(["echo", "hello"])
    assert result.returncode == 0
    assert result.stdout == "hello\n"
```

## Open Questions

1. **Should we support `shell=False` with string commands?**
    - Current thinking: No, confusing and error-prone
    - If user wants non-shell string, use list: `[cmd_string]`

2. **Should we provide a `safe_run()` helper for untrusted input?**
    - Current thinking: No, not needed initially
    - Can add later if use case emerges

## Risk Mitigation

### Security: Shell Injection

- Add prominent security warning in docstring
- Document safe usage patterns
- Provide examples of safe vs unsafe usage

### Type Complexity

- Clear docstring with examples
- Type narrowing makes it intuitive
- IDE autocomplete shows correct options

## Success Criteria

- [ ] String commands execute correctly with shell
- [ ] Command chaining works: `cmd1 && cmd2`
- [ ] Pipes work: `cmd1 | cmd2`
- [ ] Wildcards work: `*.py`
- [ ] Redirects work: `> file.txt`
- [ ] PTY color preservation works with shell
- [ ] All existing tests pass (623+)
- [ ] Type checking passes without errors
