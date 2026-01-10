# Bakelib Mixin System - Plan

## Overview

Design and implement `src/bakelib/` - a collection of reusable `Bakebook` subclasses that provide pre-built commands and functionality.

**Key Insight:** No "Recipe" or "Mixin" concept needed. Everything is a Bakebook. Multiple inheritance provides composition.

**Naming:**

- `PythonSpace`, `RustSpace`, `PreCommit`, `Docker` (simple, descriptive)
- `PythonProject` for precomposed classes

---

## High-Level Requirements

### 1. Language-Specific Space Classes

Bakebook subclasses for different languages:

```python
from bake import Bakebook, command

class PythonSpace(Bakebook):
    """Python project with lint, test, and uv commands."""

    @command()
    def lint(self) -> None:
        """Run ruff."""
        ...

    @command()
    def test(self) -> None:
        """Run pytest."""
        ...

    @command()
    def install(self) -> None:
        """Run uv install."""
        ...

    @command()
    def lock(self) -> None:
        """Run uv lock."""
        ...
```

Other language implementations:

- **RustSpace**: `cargo clippy`, `cargo test`
- **JavaScriptSpace**: `eslint`, `vitest/jest`

### 2. Tool Classes

Composable Bakebook subclasses for specific tools:

```python
class PreCommit(Bakebook):
    """Pre-commit hooks management."""

    @command()
    def setup_precommit(self) -> None:
        """Install pre-commit hooks."""
        ...

    @command()
    def run_precommit(self) -> None:
        """Run pre-commit on all files."""
        ...
```

- **Docker**: docker build, push, etc.

### 3. Usage Pattern

Users compose via multiple inheritance:

```python
from bake import Bakebook
from bakelib.space import PythonSpace
from bakelib.tools import PreCommit

class MyBakebook(PreCommit, PythonSpace, Bakebook):
    """My project with Python tools + pre-commit."""
    pass
```

This automatically provides:

- `bake lint` (ruff)
- `bake test` (pytest)
- `bake install` (uv)
- `bake setup-precommit`
- `bake run-precommit`

### 4. Precomposed Classes

Optional convenience classes for common setups:

```python
class PythonProject(PythonSpace, Bakebook):
    """Ready-to-use Python project Bakebook."""
    pass
```

---

## Decisions

### Q1: ABC or Not?

**Decision: Optional, use if needed**

ABC is not required. Use `ABC` with `@abstractmethod` only if you want to enforce a contract. Simple inheritance works fine.

---

### Q2: Command Merging Strategy

**Decision: Normal Python MRO**

Standard Method Resolution Order. Leftmost in inheritance list wins.

```python
class MyBakebook(PreCommit, PythonSpace, Bakebook):
    pass
# MRO: MyBakebook → PreCommit → PythonSpace → Bakebook
```

If both `PreCommit` and `PythonSpace` define `lint()`, `PreCommit` wins (leftmost).

---

### Q3: Conflict Resolution

**Decision: Leftmost wins, user calls super() if needed**

If two classes define the same command, the leftmost wins. Users who want both behaviors explicitly call `super()`.

```python
class MyBakebook(PythonSpace, Bakebook):
    @command()
    def test(self):
        """Run pytest with coverage."""
        super().test()  # Call PythonSpace.test()
        # Add coverage report
```

**Important:**

- Method override **without** `@command` loses command registration
- Method override **with** `@command` replaces parent registration

---

### Q4: Dependencies Between Classes

**Decision: Multiple inheritance handles it**

No `__requires__` needed. Use multiple inheritance:

```python
class MyBakebook(Docker, PythonSpace, Bakebook):
    pass  # Gets both Docker and PythonSpace commands
```

If one class "depends" on another, just include both in the inheritance list.

---

### Q5: Discovery API

**Decision: Direct import, optional CLI**

#### Primary: Direct Import

```python
from bakelib.space import PythonSpace, RustSpace
from bakelib.tools import PreCommit, Docker
```

#### Optional: CLI Command

```bash
$ bake recipes
Available bakelib classes:
  PythonSpace    Python project with ruff + pytest + uv
  RustSpace      Rust project with cargo clippy + test
  PreCommit      Pre-commit hooks management
  Docker         Docker build and push commands
```

Simple introspection - no decorator registration needed.

---

### Q6: Type Checking

**Decision: Use protocols or intersections if needed**

For type checking composed Bakebooks:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ty import Intersection

    type PythonProjectBakebook = Intersection[Bakebook, PythonSpace]

def takes_python_bakebook(bb: PythonProjectBakebook) -> None:
    bb.lint()  # Type checker knows this exists
    bb.test()  # And this
```

Or use a Protocol if you prefer.

---

### Q7: Naming Convention (FINAL)

**Decision: Simple, descriptive names**

| Concept     | Naming Pattern     | Examples                   |
| ----------- | ------------------ | -------------------------- |
| Base class  | `[Purpose]`        | `PythonSpace`, `PreCommit` |
| Precomposed | `[Scope][Purpose]` | `PythonProject`            |

**Rationale:**

- No "Recipe", "Mixin", or "BaseRecipe" terminology
- Everything is a Bakebook subclass
- Simple and clear

```python
# Base class
class PythonSpace(Bakebook):
    def lint(self): ...

# Precomposed
class PythonProject(PythonSpace, Bakebook):
    pass
```

---

## File Structure

```
src/bakelib/
├── __init__.py
└── space/
    ├── __init__.py
    ├── python.py      # PythonSpace
    ├── rust.py        # RustSpace
    ├── javascript.py  # JavaScriptSpace
    └── tools/
        ├── __init__.py
        ├── precommit.py  # PreCommit
        └── docker.py     # Docker
```

**Notes:**

- `python.py` includes uv functionality (opinionated but convenient)
- `space/tools/` contains tool Bakebooks
- Precomposed classes optional - users compose themselves

---

## Next Steps

1. [x] Resolve naming convention
2. [x] Test multiple inheritance behaviors (comprehensive tests in `test_inheritance.py`)
3. [ ] Implement `PythonSpace` as proof of concept
4. [ ] Implement `PreCommit` tool class
5. [ ] Implement optional `bake recipes` CLI command
6. [ ] Add more language implementations (Rust, JavaScript)
