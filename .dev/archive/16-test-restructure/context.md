# Test Restructure - Context

Last Updated: 2025-01-17

## SESSION PROGRESS (2025-01-17)

### ✅ COMPLETED - ALL PHASES

**Phase 1: Prepare Structure - COMPLETE**

- Dev docs structure created (`.dev/active/16-test-restructure/`)
- Comprehensive plan written
- Created directory structure:
    - `tests/unit/`
    - `tests/integration/examples/`
    - `tests/integration/fixtures/`
- Added `.gitkeep` files to new directories
- **Removed `@pytest.mark.integration` marker from `pyproject.toml`** (deleted lines 52-55)
- Verified `pyproject.toml` syntax is valid

**Phase 2: Move Existing Tests to unit/ - COMPLETE**

- Moved `tests/bake/` → `tests/unit/bake/` using `git mv`
- Moved `tests/bakelib/` → `tests/unit/bakelib/` using `git mv`
- **Important Decision:** Kept `tests/utils/` at root (not moved to `tests/unit/utils/`) because it's shared by both unit and integration tests
- Removed all `@pytest.mark.integration` decorators from test files:
    - `tests/unit/bake/cli/bakefile/test_bakefile_init.py` (3 removed)
    - `tests/unit/bake/cli/bakefile/test_bakefile_lint.py` (8 removed)
- Fixed all import paths after directory restructuring
- Fixed `examples_simple_dir` fixture path calculation in `tests/utils/paths.py`
- **All 824 tests pass**
- **All lint checks pass** (ruff, ty, prettier, toml-sort)

**Phase 3: Update Makefile - COMPLETE**

- Updated `make test` to run only `tests/unit/`
- Added `make test-integration` target
- Added `make test-all` target
- Verified all targets work correctly:
    - `make test`: 824 unit tests in ~51s
    - `make test-integration`: 1 integration test in ~17-27s
    - `make test-all`: All 825 tests with coverage

**Phase 4: Create First Integration Test - COMPLETE**

- Created `tests/integration/fixtures/bake/` directory
- Created `tests/integration/fixtures/bake/test_reinvocation.py`
- Ported the `test_reinvocation_actually_switches_python` test from commented code
- Removed 37 lines of commented code from `tests/unit/bake/cli/bake/test_reinvocation.py`
- Integration test passes (runs in ~17-27 seconds)

**Phase 5: Documentation - COMPLETE**

- Updated `.claude/CLAUDE.md` with test structure explanation
- Created `tests/README.md` with comprehensive testing documentation
- Documented when to write unit vs integration tests
- Added examples of how to run different test types

## Key Files Modified

### Configuration Files

- `pyproject.toml` - Removed `[tool.pytest.ini_options]` section with integration marker
- `Makefile` - Updated test target, added test-integration and test-all targets

### Directory Structure Changes

- Created: `tests/unit/`, `tests/integration/examples/`, `tests/integration/fixtures/`
- Moved: `tests/bake/` → `tests/unit/bake/`
- Moved: `tests/bakelib/` → `tests/unit/bakelib/`
- Kept: `tests/utils/` at root (shared utilities)

### Import Path Updates (11 files)

- `tests/conftest.py` - Updated to import from `tests.utils`
- `tests/utils/projects.py` - Updated imports
- `tests/utils/__init__.py` - Updated imports
- `tests/unit/bake/bakebook/test_decorator.py` - Updated imports from `tests.bake` → `tests.unit.bake`
- `tests/unit/bake/bakebook/test_inheritance.py` - Updated imports
- `tests/unit/bake/bakebook/test_bakebook.py` - Updated imports
- `tests/unit/bake/ui/logger/test_logger_setup.py` - Updated imports
- `tests/unit/bake/ui/logger/test_capsys.py` - Updated imports
- `tests/unit/bake/ui/run/test_run.py` - Updated imports
- `tests/unit/bake/ui/run/test_script.py` - Updated imports

### Decorator Removal (2 files)

- `tests/unit/bake/cli/bakefile/test_bakefile_init.py` - Removed 3 `@pytest.mark.integration` decorators
- `tests/unit/bake/cli/bakefile/test_bakefile_lint.py` - Removed 8 `@pytest.mark.integration` decorators

### Integration Test Created

- `tests/integration/fixtures/bake/test_reinvocation.py` - First real integration test (slow, real subprocess)

### Documentation Created

- `tests/README.md` - Comprehensive testing guide with examples

### Documentation Updated

- `.claude/CLAUDE.md` - Added test structure section and updated commands

### Source Code Updated

- `src/bakelib/space/python.py` - Updated `test()` method to check for `tests/unit/` first, fall back to `tests/` for backward compatibility. Added `test_integration()` method for integration tests.

## Important Decisions

### Directory Structure Decision

**Chosen:** Directory-based separation (`tests/unit/`, `tests/integration/`)
**Reasoning:**

- Clear physical separation
- Easy to exclude entire directories
- More maintainable than marker-based
- Aligns with user preference for clear organization

### Test Utilities Location

**Decision:** Keep `tests/utils/` at root (NOT moved to `tests/unit/utils/`)
**Rationale:**

- Test utilities are used by both unit AND integration tests
- Moving them to `tests/unit/utils/` would require integration tests to import from `tests.unit.utils`
- Keeping at root allows both test types to import from `tests.utils`

### Integration Test Categories

**`tests/integration/examples/`**

- Purpose: Tests against real examples in `@examples/`
- Characteristics: Real subprocess calls, uses actual example projects
- Examples: `examples/simple/`, `examples/python-package/`

**`tests/integration/fixtures/`**

- Purpose: Tests using temp fixture folders
- Characteristics: Real subprocess calls, but with isolated temp environments
- Tests that create fresh project folders per test via fixtures

### Marker Removal

**Decision:** Remove `@pytest.mark.integration` marker entirely
**Status:** ✅ COMPLETE

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

## Test Execution Commands

**Updated Commands:**

```bash
make test              # Unit tests only (fast, ~50s)
make test-integration  # Integration tests only (slow, ~17-27s)
make test-all          # Everything with coverage
```

## Quick Resume

**All phases complete!**

The test restructure is finished. The project now has:

- 824 fast unit tests in `tests/unit/` (~50 seconds)
- 1 slow integration test in `tests/integration/fixtures/bake/` (~17-27 seconds)
- Separate make targets for running different test types
- Comprehensive documentation in `tests/README.md` and `.claude/CLAUDE.md`
- Source code updated to support new test structure (`PythonSpace.test()` checks for `tests/unit/` first)

**Next Steps:**

- Ready to commit changes
- Can add more integration tests to `tests/integration/examples/` as needed
- All existing workflows updated to use new test structure
