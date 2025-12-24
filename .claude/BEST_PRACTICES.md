# BEST_PRACTICES.md

**Coding standards and patterns for bakefile**

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
