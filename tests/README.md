# Tests

This directory contains the test suite for the bakefile project.

## Directory Structure

```
tests/
├── unit/              # Fast unit tests
│   ├── bake/         # Bake-specific tests
│   │   ├── bakebook/
│   │   ├── cli/
│   │   ├── manage/
│   │   └── ui/
│   └── bakelib/      # Bakelib tests
│       └── space/
├── integration/      # Slow integration tests
│   ├── examples/     # Tests against @examples/
│   └── fixtures/     # Tests using temp fixture folders
├── utils/            # Shared test utilities
└── conftest.py       # Shared fixtures
```

## Test Types

### Unit Tests (`tests/unit/`)

**Characteristics:**

- Use mocks to avoid subprocess calls
- Test logic in isolation
- No external dependencies

**When to write unit tests:**

- Testing individual functions or methods
- Testing class behavior in isolation
- Testing business logic without external dependencies
- Default choice for new tests

**Examples:**

```python
# Unit test with mocked subprocess
def test_reinvoke_with_detected_python(subprocess_mock, monkeypatch):
    # Mock subprocess.run to prevent real execution
    monkeypatch.setattr("subprocess.run", fake_run)
    _reinvoke_with_detected_python(Path("bakefile.py"))
    assert len(subprocess_mock) == 1
```

### Integration Tests (`tests/integration/`)

**Characteristics:**

- Slow (15-30+ seconds per test)
- Run real subprocess commands
- Test end-to-end behavior
- Use actual example projects or temporary fixtures

**Two categories:**

1. **`tests/integration/examples/`** - Tests against real examples
    - Test actual example projects in `@examples/`
    - Verify bake commands work against real code
    - Example: Testing `bake hello` against `examples/simple/`

2. **`tests/integration/fixtures/`** - Tests with temporary fixtures
    - Create fresh project folders per test via fixtures
    - Test CLI behavior in isolated environments
    - Example: Testing Python reinvocation with UV project

If a re-invoked script environment runs old code, uv reused a stale build of the local package: run `uv cache clean bakefile`.

**When to write integration tests:**

- Testing real subprocess behavior
- Testing end-to-end flows that can't be mocked
- Testing against actual example projects
- Verifying CLI commands work as expected

**Examples:**

```python
# Integration test with real subprocess
def test_reinvocation_actually_switches_python(
    uv_project_folder_with_deps: Path,
):
    # Runs actual bake command via subprocess
    result = run(["bake", "-vv", "test-dep"], check=False, cwd=uv_project_folder_with_deps)
    assert result.returncode == 0
```

## Running Tests

### Quick Reference

```bash
# Run all unit tests (fast, default)
bake test

# Run all integration tests (slow)
bake test-integration

# Run everything with coverage
bake test-all
```

### Running Specific Tests

**Unit tests:**

```bash
# Run specific unit test file
uv run pytest tests/unit/bakelib/space/test_space_base.py -v

# Run specific unit test
uv run pytest tests/unit/bakelib/space/test_space_base.py::test_recipe_with_bakebook_succeeds -v

# Run all unit tests in a directory
uv run pytest tests/unit/bakelib/ -v

# Run all unit tests (same as bake test)
uv run pytest tests/unit/ --cov=src --cov-report=html
```

**Integration tests:**

```bash
# Run specific integration test
uv run pytest tests/integration/fixtures/bake/test_reinvocation.py -v

# Run all integration tests in a category
uv run pytest tests/integration/fixtures/ -v

# Run all integration tests (same as bake test-integration)
uv run pytest tests/integration/ -v
```

### During Development

**For fast feedback, run specific tests:**

```bash
# After modifying a specific file
uv run pytest tests/unit/path/to/modified_file.py -v

# After modifying a specific function
uv run pytest tests/unit/path/to/file.py::test_specific_function -v

# Run all tests in a module
uv run pytest tests/unit/bakelib/space/ -v
```

**Before committing:**

```bash
# Run full unit test suite
bake test

# Run linting
bake lint
```

### Managed Content Templates

Every template in a `managed/` folder anywhere under `src/` has an expected output in `tests/unit/bakelib/managed_content/expected/`, at the template's path relative to `src/` plus an `.expected` suffix (so formatters and config discovery ignore it). For example, `src/bakelib/space/managed/oxfmt-config.ts` maps to `expected/bakelib/space/managed/oxfmt-config.ts.expected`. Its content is the file as `bake mc sync` writes it from the Space defaults. A child Space that changes a parent's template (`insert`, `set_default`) gets its own expected file, `<template>@<Space>.expected`. Python modules in `managed/` hold template strings and need no expected file. Beside it, `<template>.blocks.expected` lists the template's editable block names, one per line. Block names are the keys in `bake.lock`, so a rename drops every repo's edits to that block; the snapshot makes a rename fail until it is accepted in review. After adding or changing a template, rewrite the expected files and snapshots and review their diff:

```bash
BAKE_UPDATE_EXPECTED=1 uv run pytest tests/unit/bakelib/managed_content/test_templates.py
```

The checks live in `bakelib.managed_content.testing.TemplateSuite`, so a package that ships its own Spaces and `managed/` folders reuses them with its own package names and expected folder. `test_templates.py` is the example to copy.

Unit tests never fetch github/gitignore templates from the network. An autouse fixture in `tests/unit/conftest.py` patches `BaseSpace._get_gitignore_upstream()` to `STAND_IN_GITIGNORE` (`bakelib.managed_content.testing`), which writes one line per template, so Space commands that sync a `.gitignore` stay offline. `TemplateSuite` uses the same stand-in unless it is given `gitignore_upstream`. `test_templates.py` passes one that reads a snapshot of the templates the Spaces list (the three `Global/` ones and `Python`) in `github_gitignore/`, so the expected `.gitignore` shows real content; refresh the snapshot by hand when you want newer upstream text.

## Test Utilities

Shared test utilities are available in `tests/utils/`:

- `cli.py` - CLI running utilities
- `configs.py` - Test configuration helpers
- `context.py` - Context mocking utilities
- `env_vars.py` - Environment variable isolation
- `logger.py` - Logger state management
- `paths.py` - Path fixtures
- `projects.py` - Project fixtures (UV projects, empty folders, etc.)
- `flaky.py` - Flaky test handling

## Shared Fixtures

Available in `tests/conftest.py`:

- `run_cli` - Run CLI commands for testing
- `empty_project_folder` - Empty temporary project folder
- `uv_project_folder` - UV project with bakefile
- `uv_project_folder_with_deps` - UV project with dependencies
- `examples_simple_dir` - Path to examples/simple/
- `isolate_virtual_env` - Isolate from virtual environment
- `prevent_reinvocation` - Prevent bake from reinvoking
- `isolate_global_config_dir` (autouse) - Point `BAKE_CONFIG_DIR` and `XDG_CONFIG_HOME` (env vars and the already-loaded `bake_settings` fields) at an empty temp directory
- `remove_test_script_envs` (autouse) - At teardown, delete the uv script environment of any standalone `bakefile.py` in the test's `tmp_path` (or one level below), so tests do not leak `environments-v2/bakefile-*` folders into the real uv cache

## Guidelines

### Writing New Tests

1. **Default to unit tests** - They're fast and reliable
2. **Use integration tests sparingly** - Only when real subprocess behavior is essential
3. **Mock subprocess calls** - In unit tests, use `unittest.mock.patch` or fixture-based mocks
4. **Use descriptive test names** - `test_<what>_<expected_outcome>` format
5. **Keep tests focused** - One assertion per test when possible

### Test Organization

- Place tests in `tests/unit/` mirroring the `src/` structure
- Place integration tests in `tests/integration/examples/` or `tests/integration/fixtures/`
- Use shared fixtures from `tests/conftest.py` when available
- Add new utilities to `tests/utils/` when they're needed by both unit and integration tests

### Common Patterns

**Unit test with mocks:**

```python
from unittest.mock import patch


def test_my_function(monkeypatch):
    # Mock external dependencies
    monkeypatch.setattr("module.subprocess.run", fake_run)

    # Test the function
    result = my_function()
    assert result == expected
```

**Integration test with real subprocess:**

```python
from bake.ui import run


def test_real_command(uv_project_folder: Path):
    # Run actual command
    result = run(["bake", "command"], check=False, cwd=uv_project_folder)

    # Verify real behavior
    assert result.returncode == 0
    assert "expected output" in result.stdout
```

## Coverage Goals

- Unit tests should cover core logic paths
- Integration tests cover critical user workflows
- Coverage reports are generated in `htmlcov/` after running `bake test` or `bake test-all`
- Target: Maintain >90% coverage for core modules
