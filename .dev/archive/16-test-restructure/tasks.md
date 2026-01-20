# Test Restructure - Task Checklist

Last Updated: 2025-01-17

## Phase 1: Prepare Structure ✅ COMPLETE

- [x] Create `tests/unit/` directory
- [x] Create `tests/integration/examples/` directory
- [x] Create `tests/integration/fixtures/` directory
- [x] Add `.gitkeep` files to new directories
- [x] Remove `@pytest.mark.integration` marker from `pyproject.toml` (lines 52-55)
- [x] Verify `pyproject.toml` syntax is correct

**Completed:** 2025-01-17

## Phase 2: Move Existing Tests to unit/ ✅ COMPLETE

- [x] Move `tests/bake/` → `tests/unit/bake/`
- [x] Move `tests/bakelib/` → `tests/unit/bakelib/`
- [x] Keep `tests/utils/` at root (shared by unit and integration tests)
- [x] Verify `tests/conftest.py` remains at root
- [x] Remove `@pytest.mark.integration` from `tests/unit/bake/cli/bakefile/test_bakefile_init.py` (3 occurrences)
- [x] Remove `@pytest.mark.integration` from `tests/unit/bake/cli/bakefile/test_bakefile_lint.py` (8 occurrences)
- [x] Fix import paths after directory restructuring
- [x] Fix `examples_simple_dir` fixture path calculation
- [x] Run `uv run pytest tests/unit/ -v` to verify tests pass (824 passed)
- [x] Run `make lint` to check for import issues (all checks pass)

**Completed:** 2025-01-17

## Phase 3: Update Makefile ✅ COMPLETE

- [x] Update `make test` to run only `tests/unit/`
- [x] Add `make test-integration` target (all integration tests)
- [x] Add `make test-all` target (everything with coverage)
- [x] Test `make test` runs fast (824 tests in ~51s)
- [x] Test `make test-integration` runs integration tests
- [x] Test `make test-all` runs everything with coverage

**Completed:** 2025-01-17

**Files Modified:**

- `Makefile` - Updated test target, added test-integration and test-all targets

## Phase 4: Create First Integration Test ✅ COMPLETE

- [x] Create `tests/integration/fixtures/bake/` directory
- [x] Create `tests/integration/fixtures/bake/test_reinvocation.py`
- [x] Uncomment the `test_reinvocation_actually_switches_python` test
- [x] Add necessary imports (from commented code)
- [x] Verify test passes with `uv run pytest tests/integration/fixtures/bake/test_reinvocation.py -v`
- [x] Remove commented code from `tests/unit/bake/cli/bake/test_reinvocation.py`

**Completed:** 2025-01-17

**Files Created:**

- `tests/integration/fixtures/bake/test_reinvocation.py` - First real integration test

**Files Modified:**

- `tests/unit/bake/cli/bake/test_reinvocation.py` - Removed 37 lines of commented code

## Phase 5: Documentation ✅ COMPLETE

- [x] Update `.claude/CLAUDE.md` with test structure explanation
- [x] Create `tests/README.md` documenting the organization
- [x] Document when to write unit vs integration tests
- [x] Add examples of how to run different test types

**Completed:** 2025-01-17

**Files Created:**

- `tests/README.md` - Comprehensive testing documentation

**Files Modified:**

- `.claude/CLAUDE.md` - Added test structure section, updated commands

**Additional Changes:**

- `src/bakelib/space/python.py` - Updated `test()` method to check for `tests/unit/` first, fall back to `tests/` for backward compatibility. Added `test_integration()` method for integration tests.

## Quick Resume

**All phases complete!**

The test restructure is finished. The project now has:

- 824 fast unit tests in `tests/unit/` (~50 seconds)
- 1 slow integration test in `tests/integration/fixtures/bake/` (~17-27 seconds)
- Separate make targets: `make test`, `make test-integration`, `make test-all`
- Comprehensive documentation in `tests/README.md` and `.claude/CLAUDE.md`

## Final Test Structure

```
tests/
├── unit/                    # Fast unit tests (824 tests)
│   ├── bake/
│   │   ├── bakebook/
│   │   ├── cli/
│   │   ├── manage/
│   │   └── ui/
│   └── bakelib/
│       └── space/
├── utils/                   # Shared test utilities
├── conftest.py             # Shared fixtures
├── README.md               # Testing documentation
└── integration/            # Slow integration tests (1 test)
    ├── examples/           # Tests against @examples/
    └── fixtures/           # Tests with temp fixture folders
        └── bake/
            └── test_reinvocation.py
```

## Summary of All Files Modified/Created

**Configuration Files:**

- `pyproject.toml` - Removed integration marker
- `Makefile` - Added test-integration, test-all targets; updated test target

**Test Files Moved:**

- `tests/bake/` → `tests/unit/bake/` (via git mv)
- `tests/bakelib/` → `tests/unit/bakelib/` (via git mv)
- `tests/utils/` - Kept at root for sharing

**Test Files Modified:**

- 11 test files - Updated import paths after restructuring
- 2 test files - Removed `@pytest.mark.integration` decorators

**Integration Test Created:**

- `tests/integration/fixtures/bake/test_reinvocation.py`

**Documentation Created:**

- `tests/README.md` - Comprehensive testing guide

**Documentation Updated:**

- `.claude/CLAUDE.md` - Added test structure documentation

**Source Code Updated:**

- `src/bakelib/space/python.py` - Updated test methods for new structure
