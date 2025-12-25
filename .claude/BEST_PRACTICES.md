# BEST_PRACTICES.md

**Coding standards and patterns for bakefile**

## Naming Conventions

### bakebook Variable Name

**Always use `bakebook` (not `bakebook_app`, `bakebook_cli`, etc.)**

This applies consistently across:

- User's `bakefile.py`
- Internal variable names in `bake` CLI
- Test files
- Documentation

```python
# Good
bakebook = typer.Typer()

# Bad
bakebook_app = typer.Typer()
bakebook_cli = typer.Typer()
```

---

## Documentation

### Docstring Format

**Use NumPy format for multi-line docstrings:**

```python
from typing import TypeVar

T = TypeVar("T")

def validate_value(value: Any, expected_type: type[T]) -> T:
    """Validate that value matches expected type.

    Parameters
    ----------
    value : Any
        The value to validate
    expected_type : type[T]
        The expected type to check against

    Returns
    -------
    T
        The validated value

    Raises
    ------
    SystemExit
        If validation fails
    """
```

### When to Omit Docstrings

**Omit docstrings that add no value beyond the function name:**

```python
# Bad - redundant, function name is self-explanatory
def validate_file_name(file_name: str) -> None:
    """Validate file_name is a filename (not a path) and ends with .py."""
    # Implementation...

# Good - no docstring, function name says it all
def validate_file_name(file_name: str) -> None:
    # Implementation...
```

**Use docstrings when:**

- Function has **multiple parameters** to document
- Function has **complex behavior** not obvious from name
- Function **raises exceptions** worth documenting
- Public API that needs **usage documentation**

**Omit docstrings when:**

- Function name is **self-explanatory** (`validate_file_name`, `change_directory`)
- Implementation is **obvious** from code
- Private/internal functions
- `__init__.py` files

---

## Testing Practices

### Test Folder Structure

Tests mirror the source folder structure for easy navigation and maintainability.

**Example:**

```
src/bakefile/cli/          tests/cli/
├── __init__.py         →  ├── __init__.py
├── bake.py             →  ├── test_bake.py
└── bakefile.py         →  └── test_bakefile.py
```

**Rules:**

- Create corresponding test file in `tests/` for each module in `src/`
- Use `test_` prefix for test files
- Maintain same directory hierarchy
- Each test file should test its corresponding source module

---

---

## Bakebook Pattern

### User's bakefile.py

Users define their bakebook as a `typer.Typer` app with commands as methods:

```python
import typer

bakebook = typer.Typer()

@bakebook.command()
def build(
    prod: bool = typer.Option(False, "--prod", help="Production build"),
):
    """Build the project."""
    typer.echo(f"Building{' (prod)' if prod else ''}...")

@bakebook.command()
def test(
    coverage: bool = typer.Option(False, "--coverage", help="Run with coverage"),
):
    """Run tests."""
    typer.echo("Running tests...")

@bakebook.command()
def lint():
    """Run linters."""
    typer.echo("Running linters...")
```

### Running Commands

```bash
# List all commands (shows help)
bake -C /path/to/project

# Run a specific command
bake -C /path/to/project build --prod

# With custom bakefile name
bake -f custom_tasks.py test

# With custom bakebook variable name
bake -b my_tasks build
```

### Bakebook Evolution

| Phase        | bakebook Type    | Description                    |
| ------------ | ---------------- | ------------------------------ |
| v0 (past)    | `str`            | Temporary placeholder          |
| v1 (current) | `typer.Typer`    | Commands only                  |
| v2 (future)  | `Bakebook` class | Full OOP: commands + variables |

---

## Sections to Add:

- Code conventions
- Design patterns used
- File organization standards
- Error handling patterns
