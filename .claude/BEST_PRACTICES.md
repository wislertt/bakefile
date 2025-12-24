# BEST_PRACTICES.md

**Coding standards and patterns for bakefile**

## Documentation

### Docstring Format

**Use NumPy format for multi-line docstrings:**

```python
def resolve_bakebook(file_name: str, bakebook_name: str, chdir: str | None = None) -> str:
    """Load a bakefile and retrieve a bakebook object.

    Parameters
    ----------
    file_name : str
        Name of the .py file (must end with .py, no path separators)
    bakebook_name : str
        Name of the bakebook object to retrieve
    chdir : str | None, optional
        Optional directory to change to before loading

    Returns
    -------
    str
        The bakebook object value

    Raises
    ------
    SystemExit
        If any validation or loading step fails
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

## Sections to Add:

- Code conventions
- Design patterns used
- File organization standards
- Naming conventions
- Error handling patterns
