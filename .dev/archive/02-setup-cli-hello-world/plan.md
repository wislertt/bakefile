# Setup CLI Hello World - Implementation Plan

**Last Updated: 2025-12-24**

---

## Executive Summary

Implement two CLI commands (`bake` and `bakefile`) for the bakefile project. Both commands will initially print "hello world" to stdout. This establishes the foundation for:

- `bake` - The task runner CLI that will execute bakefile.py recipes
- `bakefile` - The project management CLI for init, lint, docs operations

---

## Current State Analysis

### Existing Assets

- **Package structure**: `src/bakefile/` exists with `hello.py` (has a more complex greeting function)
- **Dependencies**: Pydantic is installed, but no CLI framework (typer) yet
- **pyproject.toml**: Has dependencies but no `[project.scripts]` entry points
- **Tests**: `tests/test_bakefile.py` exists with tests for the hello function

### Gaps

1. No typer dependency (CLI framework specified in tech stack)
2. No entry points defined in pyproject.toml
3. No CLI modules created
4. No `cli/` subdirectory structure

---

## Proposed Future State

### User Experience

```bash
# After installing the package
$ bake
hello world

$ bakefile
hello world
```

### Technical Structure

```
src/bakefile/
├── __init__.py
├── hello.py           (existing, may be replaced/simplified)
└── cli/
    ├── __init__.py
    ├── bake.py        # bake CLI entry point
    └── bakefile.py    # bakefile CLI entry point
```

### pyproject.toml additions

```toml
[project]
dependencies = [
  "pydantic>=2.12.5",
  "typer>=0.0.1",     # ADD THIS
]

[project.scripts]
bake = "bakefile.cli.bake:app"        # ADD THIS
bakefile = "bakefile.cli.bakefile:app"  # ADD THIS
```

---

## Implementation Phases

### Phase 1: Add CLI Dependency

**Task 1.1: Add typer to project dependencies**

- Add `typer` to `dependencies` in pyproject.toml
- Version: Use `typer>=0.0.1` or latest stable
- Acceptance: `uv sync` installs typer successfully
- Effort: S

---

### Phase 2: Create CLI Module Structure

**Task 2.1: Create cli/ directory and **init**.py**

- Create `src/bakefile/cli/__init__.py`
- Can be empty or have docstring
- Acceptance: Directory created, file exists
- Effort: S

---

### Phase 3: Implement bake CLI

**Task 3.1: Create src/bakefile/cli/bake.py**

- Create a simple typer app that prints "hello world"
- Use `typer.Typer()` and `@app.command()`
- Export `app` for entry point
- Acceptance: File created, typer app defined
- Effort: S

**Task 3.2: Add bake entry point to pyproject.toml**

- Add `[project.scripts]` section if not exists
- Add `bake = "bakefile.cli.bake:app"`
- Acceptance: Entry point defined
- Effort: S

---

### Phase 4: Implement bakefile CLI

**Task 4.1: Create src/bakefile/cli/bakefile.py**

- Create a simple typer app that prints "hello world"
- Same structure as bake.py
- Export `app` for entry point
- Acceptance: File created, typer app defined
- Effort: S

**Task 4.2: Add bakefile entry point to pyproject.toml**

- Add to `[project.scripts]` section
- Add `bakefile = "bakefile.cli.bakefile:app"`
- Acceptance: Entry point defined
- Effort: S

---

### Phase 5: Add CLI Tests

**Task 5.1: Create tests/cli/ directory structure**

- Create `tests/cli/__init__.py` (can be empty)
- Mirrors `src/bakefile/cli/` structure
- Acceptance: Directory and **init**.py exist
- Effort: S

**Task 5.2: Create tests/cli/test_bake.py**

- Test file for `bake` CLI
- Use typer's `CliRunner` to test the command
- Verify "hello world" output
- Acceptance: Test passes for bake command
- Effort: S

**Task 5.3: Create tests/cli/test_bakefile.py**

- Test file for `bakefile` CLI
- Use typer's `CliRunner` to test the command
- Verify "hello world" output
- Acceptance: Test passes for bakefile command
- Effort: S

---

### Phase 6: Test Both CLIs

**Task 6.1: Install package and test bake command**

- Run `uv sync` to install with new entry points
- Run `bake` command
- Verify output is "hello world"
- Acceptance: `bake` prints "hello world"
- Effort: S

**Task 6.2: Test bakefile command**

- Run `bakefile` command
- Verify output is "hello world"
- Acceptance: `bakefile` prints "hello world"
- Effort: S

**Task 6.3: Run lint and test**

- Run `make lint` to ensure code quality
- Run all tests with `make test` (including new CLI tests)
- Acceptance: Both commands pass
- Effort: M

---

## Risk Assessment and Mitigation Strategies

| Risk                                | Likelihood | Impact | Mitigation                                  |
| ----------------------------------- | ---------- | ------ | ------------------------------------------- |
| Typer version conflicts             | Low        | Medium | Use flexible version constraint (`>=0.0.1`) |
| Entry point not found after install | Medium     | Medium | Ensure `uv sync` --reinstall if needed      |
| Path issues with virtual env        | Low        | Low    | Use `uv run` for testing initially          |
| Makefile commands broken            | Low        | Medium | Verify make lint/test still work            |

---

## Success Metrics

1. **Functional**: Both `bake` and `bakefile` commands print "hello world"
2. **Installation**: Package installs correctly with entry points
3. **Code Quality**: `make lint` passes
4. **Tests**: Existing tests still pass (`make test`)

---

## Required Resources and Dependencies

### External Dependencies

- **typer** - CLI framework (needs to be added)

### Internal Files to Create/Modify

- `src/bakefile/cli/__init__.py` (new)
- `src/bakefile/cli/bake.py` (new)
- `src/bakefile/cli/bakefile.py` (new)
- `pyproject.toml` (modify)

### Tools

- `uv` - Package manager
- `make` - Test/lint runner

---

## Timeline Estimates

| Phase                           | Tasks        | Total Effort   |
| ------------------------------- | ------------ | -------------- |
| Phase 1: Add CLI Dependency     | 1 task       | S              |
| Phase 2: Create CLI Structure   | 1 task       | S              |
| Phase 3: Implement bake CLI     | 2 tasks      | S              |
| Phase 4: Implement bakefile CLI | 2 tasks      | S              |
| Phase 5: Add CLI Tests          | 3 tasks      | S              |
| Phase 6: Test Both CLIs         | 3 tasks      | M              |
| **TOTAL**                       | **14 tasks** | **~1-2 hours** |

---

## Notes

- The existing `hello.py` function is more complex than needed for a simple "hello world" - it includes timestamp, directory, and Python version info
- Consider whether to keep `hello.py` for later use or replace with simpler version
- This is foundational work for the full bakefile CLI implementation
