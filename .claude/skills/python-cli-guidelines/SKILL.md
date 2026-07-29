# Python CLI Guidelines

Production-tested patterns for building Python CLI tools using Typer, Pydantic, and UV.

## Overview

This skill provides guidelines for developing bakefile - a Python-based build system with OOP reusability.

**Tech Stack:**

- **Typer** - CLI framework
- **Pydantic** - Data validation
- **UV** - Package manager (auto-resolve Python environments)
- **pytest** - Testing
- **ty** - Type checking

---

## Quick Reference

| Topic                   | Resource                         |
| ----------------------- | -------------------------------- |
| Typer CLI patterns      | `resources/typer-patterns.md`    |
| Pydantic validation     | `resources/pydantic-patterns.md` |
| OOP design for bakefile | `resources/oop-design.md`        |
| Testing CLI tools       | `resources/testing.md`           |
| UV packaging            | `resources/packaging.md`         |
| UV integration          | `resources/uv-integration.md`    |

---

## Project Structure

```
src/bakefile/
├── __init__.py
├── cli.py              # Typer app entry point
├── core/               # Core abstractions
│   ├── task.py         # Task base class
│   └── recipe.py       # Recipe base class
├── commands/           # Built-in commands
│   ├── init.py
│   ├── lint.py
│   └── docs.py
└── utils/              # Utilities
```

---

## Key Patterns

### 1. Command Definition (Typer)

```python
import typer

app = typer.Typer()


@app.command()
def init():
    """Initialize a new bakefile.py in current directory."""
    typer.echo("Creating bakefile.py...")
```

### 2. Data Validation (Pydantic)

```python
from pydantic import BaseModel, Field


class TaskConfig(BaseModel):
    name: str = Field(..., min_length=1)
    command: str
    description: str | None = None
```

### 3. OOP Reusability

```python
from abc import ABC, abstractmethod


class Task(ABC):
    @abstractmethod
    def execute(self) -> int:
        """Execute task, return exit code."""
        pass
```

---

## Common Tasks

**Creating a new command:**

1. See `resources/typer-patterns.md` for command patterns
2. See `resources/oop-design.md` for class structure

**Adding validation:**

1. See `resources/pydantic-patterns.md` for Pydantic models

**Testing:**

1. See `resources/testing.md` for CLI testing patterns

**Packaging:**

1. See `resources/packaging.md` for pyproject.toml setup
2. See `resources/uv-integration.md` for UV environment management

---

## File Conventions

- **Commands**: `src/bakefile/commands/*.py`
- **Core**: `src/bakefile/core/*.py`
- **Tests**: `tests/test_*.py`
- **Entry point**: `src/bakefile/cli.py`

---

## Type Safety

- Use **ty** for type checking: `uv run ty check`
- All public functions must have type hints
- Use `pydantic.BaseModel` for data structures
- Validate external data at boundaries

---

## When to Use This Skill

**Activate when:**

- Editing files in `src/bakefile/**/*.py`
- Creating new Typer commands
- Designing task/recipe classes
- Adding Pydantic models
- Writing tests for CLI
- Configuring UV/pyproject.toml

**Keywords:** cli, command, typer, task, recipe, pydantic, validation, test, uv, package

---

## Related Skills

- **skill-developer** - For creating new skills
