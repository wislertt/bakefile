# Setup CLI Hello World - Context

**Last Updated: 2025-12-24**

---

## SESSION PROGRESS (2025-12-24)

### ✅ COMPLETED

- Initial exploration complete
- Dev docs structure created
- **Phase 1: Add CLI Dependency**
    - Added `typer>=0.0.1` to pyproject.toml
    - Verified with `uv sync` - typer v0.20.1 installed

### 🟡 IN PROGRESS

- None - awaiting user to continue with Phase 2

### ⏳ NOT STARTED

- Phase 2: Create CLI Structure
- Phase 3: Implement bake CLI
- Phase 4: Implement bakefile CLI
- Phase 5: Add CLI Tests
- Phase 6: Test Both CLIs

---

## Key Files

### `pyproject.toml`

**Location**: `/Users/wisl/Desktop/vault/personal-repo/bakefile/pyproject.toml`

**Current state**:

- Has `[project]` section with dependencies (pydantic only)
- Has `[dependency-groups]` with dev dependencies (ruff, pytest, etc.)
- **Missing**: `[project.scripts]` section for CLI entry points
- **Missing**: `typer` dependency

**Required changes**:

1. Add `typer>=0.0.1` to `dependencies`
2. Add `[project.scripts]` section with `bake` and `bakefile` entry points

---

### `src/bakefile/hello.py`

**Location**: `/Users/wisl/Desktop/vault/personal-repo/bakefile/src/bakefile/hello.py`

**Current state**:

- Contains `GreetingMessage` Pydantic model
- Contains `hello()` function that returns formatted greeting with:
    - "Hello from bakefile!" message
    - Current timestamp
    - Current directory
    - Python version

**Note**: This is more complex than the simple "hello world" requested. May be simplified or used for inspiration.

---

### `src/bakefile/__init__.py`

**Location**: `/Users/wisl/Desktop/vault/personal-repo/bakefile/src/bakefile/__init__.py`

**Current state**: Empty file (or nearly empty)

---

### `tests/test_bakefile.py`

**Location**: `/Users/wisl/Desktop/vault/personal-repo/bakefile/tests/test_bakefile.py`

**Note**: Contains tests for the hello function - ensure tests still pass after changes.

### `tests/cli/` Directory (TO BE CREATED)

**Purpose**: Test CLI commands - mirrors `src/bakefile/cli/` structure

**Files to create**:

- `tests/cli/__init__.py` - Empty init file
- `tests/cli/test_bake.py` - Tests for `bake` CLI
- `tests/cli/test_bakefile.py` - Tests for `bakefile` CLI

**Required tests**:

- `bake` command outputs "hello world"
- `bakefile` command outputs "hello world"

**Implementation approach**: Use typer's `CliRunner` or subprocess testing

---

## Important Decisions

### Decision 1: Use Typer for CLI Framework

**Reasoning**:

- Specified in project tech stack (CLAUDE.md)
- Modern, type-friendly CLI framework
- Good integration with Pydantic (already in use)

### Decision 2: Separate CLI Modules

**Reasoning**:

- `bake` and `bakefile` have different purposes
- Separation allows independent growth
- Follows single responsibility principle

### Decision 3: Simple "hello world" Output

**Reasoning**:

- User explicitly requested simple string output
- Existing `hello.py` is too complex for this requirement
- Can enhance later if needed

---

## Technical Constraints

1. **Python version**: >= 3.11 (specified in pyproject.toml)
2. **Package manager**: uv (for build and dependency management)
3. **Code quality**: Must pass `make lint` (ruff)
4. **Tests**: Must pass `make test` (pytest)

---

## Quick Resume

To continue implementation:

1. **Add typer dependency** to pyproject.toml
2. **Create cli directory structure**: `src/bakefile/cli/`
3. **Create bake CLI**: `src/bakefile/cli/bake.py` with typer app
4. **Create bakefile CLI**: `src/bakefile/cli/bakefile.py` with typer app
5. **Add entry points** to pyproject.toml `[project.scripts]`
6. **Install and test**: `uv sync`, then run `bake` and `bakefile`
7. **Verify**: Run `make lint` and `make test`

See tasks.md for detailed checklist.

---

## Entry Point Pattern (Reference)

```python
# src/bakefile/cli/bake.py
import typer

app = typer.Typer()

@app.command()
def main() -> None:
    """Hello world from bake."""
    typer.echo("hello world")
```

```toml
# pyproject.toml
[project.scripts]
bake = "bakefile.cli.bake:app"
```
