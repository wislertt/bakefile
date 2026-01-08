# COMPLETED: bakefile lint Command

**Completion Date:** 2026-01-03
**Task Number:** 11

---

## Summary

Implemented a `bakefile lint` command that provides a quick, strict way to lint bakefile.py and the entire project using ruff and ty.

## Files Created

| File                                            | Purpose                        |
| ----------------------------------------------- | ------------------------------ |
| `src/bake/manage/lint.py`                       | Core linting wrapper functions |
| `src/bake/cli/bakefile/lint.py`                 | CLI command implementation     |
| `tests/bake/manage/test_lint.py`                | Unit tests (12 tests)          |
| `tests/bake/cli/bakefile/test_bakefile_lint.py` | CLI tests (8 tests)            |

## Files Modified

| File                                       | Changes                                  |
| ------------------------------------------ | ---------------------------------------- |
| `src/bake/cli/bakefile/main.py`            | Added lint command registration          |
| `src/bake/utils/constants.py`              | Added CMD_LINT constant                  |
| `src/bake/ui/logger/utils.py`              | Fixed REQUIRED_KEYS() -> required_keys() |
| `tests/bake/ui/logger/utils.py`            | Fixed REQUIRED_KEYS() -> required_keys() |
| `tests/bake/cli/bake/test_reinvocation.py` | Fixed naming convention errors           |

## Key Features

- **Default behavior:** Runs ruff format, ruff check, and ty check on all Python files
- **`--only-bakefile` / `-b`:** Lint only bakefile.py
- **`--no-ruff-format`:** Skip formatting
- **`--no-ruff-check`:** Skip linting
- **`--no-ty`:** Skip type checking
- **Fail-fast:** Stops on first linter failure

## Test Results

- 20 lint-related tests pass
- All linters pass (ruff format, ruff check, ty check)

## Usage Examples

```bash
# Lint entire project
bakefile lint

# Lint only bakefile.py
bakefile lint -b

# Skip type checking
bakefile lint --no-ty

# Combine flags
bakefile lint -b --no-ty
```
