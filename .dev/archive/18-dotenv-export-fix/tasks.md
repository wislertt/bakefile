# Tasks: Fix Dotenv Export Quoting

**Last Updated:** 2025-01-19

## Phase 1: Create Dotenv-Specific Formatter

- [x] **1.1** Create `_format_dotenv_value()` function in `export.py`
    - [x] Add function after `_format_shell_value()`
    - [x] Implement alphanumeric check (no quotes needed)
    - [x] Implement single-quote-only check (use double quotes)
    - [x] Implement double-quote-only check (use single quotes)
    - [x] Implement fallback (double quotes with escaping)
    - [x] Add docstring

- [x] **1.2** Update `DotEnvExportFormatter` to use `_format_dotenv_value()`
    - [x] Modify `_format_vars()` to accept formatter function parameter
    - [x] Update `ShExportFormatter` to pass `_format_shell_value`
    - [x] Update `DotEnvExportFormatter` to pass `_format_dotenv_value`
    - [x] Verify only dotenv uses new function

## Phase 2: Complete Test Coverage

- [x] **2.1** Add expected values assertion to `test_export_dotenv_format()`
    - [x] Create expected dict with all 32 variables
    - [x] Add comparison logic (parsed != expected)
    - [x] Add helpful error messages (missing, extra, mismatched)
    - [x] Remove temporary print statement

- [x] **2.2** Run full test suite
    - [x] Run `make test`
    - [x] Run `make lint`
    - [x] Fix any issues
    - [x] Verify all tests pass

## Completed

- [x] Added `python-dotenv>=1.2.1` to dev dependencies
- [x] Added `from dotenv import dotenv_values` import to test file
- [x] Updated test to use temp file + `dotenv_values()` parsing
- [x] Verified parsed values output
