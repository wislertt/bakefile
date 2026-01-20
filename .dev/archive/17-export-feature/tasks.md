# Export Feature - Task Checklist

Last Updated: 2026-01-17

## Phase 1: Core Export Logic ✅ COMPLETE

- [x] Create export module structure (`src/bake/cli/bakefile/export.py`)
    - Acceptance: Module exists with basic function stubs
- [x] Implement field extraction from Bakebook
    - Acceptance: Can iterate over bakebook fields and get name/value pairs
- [x] Implement type conversion strategy
    - Acceptance: All Pydantic types convert correctly (primitives, list, dict, nested)

## Phase 2: Format Implementations ✅ COMPLETE

- [x] Sh format (`export KEY="value"`)
    - Acceptance: Output valid for `eval`, complex types as JSON strings
- [x] Dotenv format (`KEY="value"`)
    - Acceptance: Valid dotenv format, compatible with .env and $GITHUB_ENV
- [x] JSON format
    - Acceptance: Valid JSON using orjson with pretty-print
- [x] YAML format (optional, may defer)
    - Acceptance: Valid YAML output if implemented

## Phase 3: CLI Integration ✅ COMPLETE

- [x] Add export command to bakefile app (`main.py`)
    - Acceptance: `bakefile export` shows in `--help`
- [x] Implement CLI parameters (`--format`, `--output`)
    - Acceptance: CLI accepts all parameters correctly
- [x] Wire up bakebook loading
    - Acceptance: Loads bakebook using existing patterns

## Phase 4: Error Handling & Edge Cases ✅ COMPLETE

- [x] Handle missing bakebook
    - Acceptance: Clear error message, exit code 1
- [x] Handle empty bakebook (no args)
    - Acceptance: No crash, outputs appropriate empty format
- [x] Handle special characters in values
    - Acceptance: Proper quoting/escaping for all formats
- [x] Validate --output file path
    - Acceptance: Creates file, handles directory existence

## Phase 5: Testing 🟡 IN PROGRESS

- [x] Unit tests for format converters
    - File: `tests/unit/bake/cli/bakefile/test_bakefile_export.py`
    - Acceptance: Each format tested with various types
- [x] Unit tests for CLI
    - Acceptance: Parameter parsing and bakebook loading tested
- [ ] Integration tests
    - File: `tests/integration/fixtures/test_export.py`
    - Acceptance: End-to-end tested with real bakefile

## Phase 6: Documentation ⏳ NOT STARTED

- [ ] Add CLI help text
    - Acceptance: `bakefile export --help` is clear and useful
- [ ] Update documentation (if needed)
    - Acceptance: Feature documented with examples

## Quick Resume

**Next step:** Phase 5 - Integration tests (or Phase 6 - Documentation)

**Current status:** Phases 1-4 complete. Unit tests passing (19/19). Export command fully functional.
