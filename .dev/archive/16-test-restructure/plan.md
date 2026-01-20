# Test Restructure - Implementation Plan

Last Updated: 2025-01-17

## Executive Summary

Restructure the test suite to separate fast unit tests from slow integration tests using a directory-based approach. This improves developer experience by making `make test` fast and reliable while preserving integration test coverage for pre-commit validation.

## Current State

**Test Structure:**

```
tests/
├── bake/          # ~53 test files
│   ├── bakebook/
│   ├── cli/
│   │   ├── bake/
│   │   ├── bakefile/  # Contains @pytest.mark.integration tests
│   │   ├── common/
│   │   └── utils/
│   ├── manage/
│   └── ui/
├── bakelib/
│   └── space/
└── utils/
```

**Issues:**

1. `make test` runs all tests including slow integration tests
2. `@pytest.mark.integration` marker exists but is not used effectively
3. Integration tests marked with `@pytest.mark.integration` are not actually slow (they use fixtures/temp folders but run quickly)
4. No dedicated location for truly slow tests (real subprocess calls, examples/)
5. Commented-out test in `tests/bake/cli/bake/test_reinvocation.py:92-127` is a true integration test

**Files with `@pytest.mark.integration`:**

- `tests/bake/cli/bake/test_reinvocation.py` (1 commented test)
- `tests/bake/cli/bakefile/test_bakefile_init.py` (3 tests)
- `tests/bake/cli/bakefile/test_bakefile_lint.py` (8 tests)

## Proposed Future State

**Directory Structure:**

```
tests/
├── unit/                       # Fast unit tests (mocked, no real subprocess)
│   ├── bake/
│   ├── bakelib/
│   └── utils/
├── integration/                # Slow integration tests (real subprocess, isolated envs)
│   ├── examples/               # Real commands against @examples/
│   │   ├── test_simple.py
│   │   └── test_python_package.py
│   └── fixtures/               # Real commands against temp fixture folders
│       └── cli/
│           ├── bakefile/
│           │   ├── test_bakefile_init.py
│           │   └── test_bakefile_lint.py
│           └── bake/
│               └── test_reinvocation.py
└── conftest.py                 # Shared fixtures
```

**Key Changes:**

1. All existing tests → `tests/unit/` (including current "integration" marked tests - they're fast)
2. Remove `@pytest.mark.integration` marker from `pyproject.toml` (not needed anymore)
3. Create `tests/integration/` with two subdirectories
4. Update `Makefile` with separate targets

## Implementation Phases

### Phase 1: Prepare Structure (Foundation)

**Goal:** Create empty directory structure and update configuration

**Tasks:**

1. Create `tests/unit/` directory structure
2. Create `tests/integration/examples/` and `tests/integration/fixtures/` directories
3. Remove `@pytest.mark.integration` marker from `pyproject.toml`
4. Add `.gitkeep` files to new directories

**Acceptance:**

- Directories created with correct structure
- `pyproject.toml` no longer has integration marker

### Phase 2: Move Existing Tests to unit/

**Goal:** Relocate all 53 test files to `tests/unit/`

**Tasks:**

1. Move `tests/bake/` → `tests/unit/bake/`
2. Move `tests/bakelib/` → `tests/unit/bakelib/`
3. Move `tests/utils/` → `tests/unit/utils/`
4. Keep `tests/conftest.py` at root
5. Remove `@pytest.mark.integration` decorators from moved files
6. Update imports in affected files

**Files to Update (remove decorator):**

- `tests/unit/bake/cli/bakefile/test_bakefile_init.py` (lines 14, 42, 58)
- `tests/unit/bake/cli/bakefile/test_bakefile_lint.py` (lines 9, 20, 31, 44, 57, 68, 81, 93)
- `tests/unit/bake/cli/bake/test_reinvocation.py` (line 92 - already commented)

**Acceptance:**

- All tests run from `tests/unit/` successfully
- No `@pytest.mark.integration` decorators remain
- Import paths updated correctly

### Phase 3: Update Makefile

**Goal:** Add separate test targets for different test types

**Tasks:**

1. Update `make test` to only run unit tests
2. Add `make test-integration` target
3. Add `make test-all` target for comprehensive testing

**New Makefile Structure:**

```makefile
test:                  # Fast unit tests only
	uv run pytest tests/unit/ --cov=src ...

test-integration:      # All integration tests
	uv run pytest tests/integration/ -v

test-all:              # Everything with coverage
	uv run pytest tests/ --cov=src ...
```

**Acceptance:**

- `make test` runs fast (< 30 seconds)
- `make test-integration` runs only integration tests
- All targets produce correct results

### Phase 4: Create First Integration Test

**Goal:** Port the commented-out reinvocation test as the first real integration test

**Tasks:**

1. Create `tests/integration/fixtures/bake/` directory
2. Create `test_reinvocation.py` in fixtures
3. Uncomment and adapt the `test_reinvocation_actually_switches_python` test
4. Add necessary imports and fixtures
5. Ensure test passes

**Acceptance:**

- Test runs successfully
- Test is in correct location
- Test exercises real subprocess behavior

### Phase 5: Documentation

**Goal:** Document the new test structure

**Tasks:**

1. Update `.claude/CLAUDE.md` with test structure explanation
2. Create `tests/README.md` explaining the organization
3. Document when to write unit vs integration tests

**Acceptance:**

- Documentation is clear and comprehensive
- Future contributors understand the structure

## Risk Assessment

### Low Risk

- Moving tests to subdirectories (git handles this well)
- Updating Makefile targets

### Medium Risk

- Import path updates (many files affected)
- Test discovery issues with pytest

### Mitigation Strategies

1. Run `make lint` after all moves to catch import issues
2. Run `make test-unit` after Phase 2 to verify nothing broke
3. Use pytest's discovery to verify all tests are found

## Success Metrics

1. **Speed:** `make test` completes in < 30 seconds
2. **Coverage:** Unit test coverage remains the same
3. **Organization:** Clear separation between unit and integration tests
4. **Usability:** Developers can run fast tests during development
5. **CI/CD:** Pre-commit hooks can use `make test-all`

## Timeline Estimates

- **Phase 1:** 15 minutes - Directory structure and config
- **Phase 2:** 30 minutes - Moving tests and removing markers
- **Phase 3:** 15 minutes - Makefile updates
- **Phase 4:** 30 minutes - First integration test
- **Phase 5:** 20 minutes - Documentation

**Total:** ~2 hours

## Dependencies

- None - this is a standalone refactoring
- Git history will preserve file moves
