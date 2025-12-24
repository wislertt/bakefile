# BEST_PRACTICES.md

**Coding standards and patterns for bakefile**

## Documentation

### Docstrings and Comments

**Rule:** Omit redundant docstrings/comments that repeat what the filename or function name already conveys.

**Examples of what NOT to do:**

```python
# Bad - redundant, filename already tells us this
"""CLI commands for bakefile."""
# in src/bakefile/cli/__init__.py

# Bad - function name is self-explanatory
def greet(name: str) -> str:
    """Greet the user."""  # adds no value
    return f"Hello, {name}"
```

**When to use docstrings:**

- To explain **why** something exists, not **what** it is
- To document non-obvious behavior or edge cases
- To describe parameters/return values for complex functions
- To provide usage examples

**When to omit:**

- `__init__.py` files (directory structure is self-explanatory)
- Simple functions with descriptive names
- One-liners where the code is obvious

---

## Testing Practices

### Test Folder Structure

Tests mirror the source folder structure for easy navigation and maintainability.

**Example:**

```
src/bakefile/cli/          tests/cli/
├── __init__.py         →  ├── __init__.py
├── bake.py              →  ├── test_bake.py
└── bakefile.py          →  └── test_bakefile.py
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
