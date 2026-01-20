# Plan: Fix Dotenv Export Quoting

**Last Updated:** 2025-01-19

## Executive Summary

Fix the `bakefile export --format dotenv` command to properly handle values with quotes (especially single quotes like `don't`). The current implementation uses `shlex.quote()` which produces shell-style quoting that `python-dotenv`'s parser cannot handle.

## Current State Analysis

### Problem

- `shlex.quote("don't")` → `'don'\'t'` (shell-style quote escaping)
- `python-dotenv` parser cannot parse `'don'\'t'`
- Result: `single_quotes` and `list_with_quotes` variables are silently dropped during export

### Root Cause

- `_format_shell_value()` uses `shlex.quote()` for all formats (sh, dotenv)
- Shell quoting is more complex than dotenv quoting
- `DotEnvExportFormatter` reuses `_format_shell_value()` which is incompatible with dotenv parsers

### Affected Files

- `src/bake/cli/bakefile/export.py` - Export formatters
- `tests/unit/bake/cli/bakefile/test_bakefile_export__debug.py` - Test being developed

## Proposed Future State

1. Create `_format_dotenv_value()` function with dotenv-specific quoting
2. Update `DotEnvExportFormatter` to use the new function
3. Test validates all edge cases including multi-line and quoted values

## Implementation Phases

### Phase 1: Create Dotenv-Specific Formatter

**Task 1.1:** Create `_format_dotenv_value()` function in `export.py`

- Implement smart quote selection logic:
    - Alphanumeric only: no quotes
    - Has single quotes only: use double quotes
    - Has double quotes only: use single quotes
    - Has both or special chars: use double quotes with escaping
- Acceptance: Function produces valid dotenv format for all test cases

**Task 1.2:** Update `DotEnvExportFormatter` to use `_format_dotenv_value()`

- Replace `_format_shell_value()` call
- Keep `_format_shell_value()` for `ShExportFormatter`
- Acceptance: Only dotenv formatter uses new function

### Phase 2: Complete Test Coverage

**Task 2.1:** Add expected values assertion to `test_export_dotenv_format()`

- Create expected dict matching `ComplexVarsBakebook` values
- Compare parsed dotenv output with expected
- Include helpful error messages for mismatches
- Acceptance: Test passes with all 32 variables

**Task 2.2:** Run full test suite to ensure no regressions

- Run `make test`
- Run `make lint`
- Acceptance: All tests pass, no new lint errors

## Risk Assessment

| Risk                           | Probability | Impact | Mitigation                                         |
| ------------------------------ | ----------- | ------ | -------------------------------------------------- |
| Breaking existing dotenv files | Low         | Medium | Add comprehensive test coverage                    |
| Edge cases not covered         | Medium      | Low    | Use existing test cases from `ComplexVarsBakebook` |
| Performance impact             | Very Low    | None   | Simple string operations                           |

## Success Metrics

- `test_export_dotenv_format()` passes with all 32 variables
- No warnings from `python-dotenv` parser
- Existing tests continue to pass

## Required Resources

- `python-dotenv>=1.2.1` (already added to dependencies)
- ~1 hour development time

## Timeline Estimate

- Phase 1: 30 minutes
- Phase 2: 30 minutes
- Total: ~1 hour
