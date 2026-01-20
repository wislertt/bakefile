# Context: Fix Dotenv Export Quoting

**Last Updated:** 2025-01-19

## Key Files

### Source Code

- `src/bake/cli/bakefile/export.py` - Export formatters, `_format_shell_value()`, `DotEnvExportFormatter`
- `tests/utils/bakefiles/complex_vars.py` - `ComplexVarsBakebook` with edge case values

### Test Files

- `tests/unit/bake/cli/bakefile/test_bakefile_export__debug.py` - Test being developed
- `tests/conftest.py` - Shared fixtures including `complex_vars_project`

### Dependencies

- `pyproject.toml` - Added `python-dotenv>=1.2.1` to dev dependencies

## Key Decisions

### Why Not Use `python-dotenv`'s `set_key()`

- `python-dotenv`'s own quoting logic (`value.replace("'", "\\'")`) produces `'don\'t'`
- Their parser cannot handle `\'` inside single quotes
- Same issue exists in their library - need custom solution

### Smart Quote Selection Strategy

```python
def _format_dotenv_value(value: str) -> str:
    if value.isalnum():
        return value
    if "'" in value and '"' not in value:
        return f'"{value}"'           # don't → "don't"
    if '"' in value and "'" not in value:
        return f"'{value}'"           # say "hello" → 'say "hello"'
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'
```

### Test Approach

- Write output to temp file
- Parse with `dotenv_values()` to handle multi-line values
- Compare parsed dict with expected values

## Dependencies

- Must have `python-dotenv` installed: `uv sync --group dev`
- Test uses `ComplexVarsBakebook` fixture

## Technical Notes

### `shlex.quote()` vs Dotenv Quoting

| Input         | `shlex.quote()` | Dotenv Needed   |
| ------------- | --------------- | --------------- |
| `don't`       | `'don'\'t'`     | `"don't"`       |
| `say "hello"` | `'say "hello"'` | `'say "hello"'` |
| `hello world` | `'hello world'` | `'hello world'` |

### Multi-line Values

- `dotenv_values()` correctly handles multi-line values
- Test writes to temp file first, then parses
- Avoids `.split("\n")` which breaks multi-line values
