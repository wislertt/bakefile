# CLAUDE.md

Guidance for Claude Code (claude.ai/code) working on this repository.

## Project

**bakefile** is a Python-based task runner (Make/Justfile alternative) that uses OOP for task/recipe reusability.

**Why:** Programmatic task runner like Makefile but reusable and uses Python.

**Language-agnostic:** While `bakefile.py` is Python, bakefile can manage tasks for any project type (Go, Rust, JS, etc.).

**Two CLIs:**

- `bake` - Runs tasks from `bakefile.py`
- `bakefile` - Manages bakefile projects (init, lint, docs)

**Tech Stack:** Typer, Pydantic, UV, pytest, ty

## Essential Commands

```bash
bake test              # Run unit tests with coverage (fast)
bake test-integration  # Run integration tests (slow, real subprocess)
bake test-all          # Run all tests with coverage
bake lint              # Run linters and formatters
```

**Development setup commands:**

```bash
bake setup-dev         # Setup development environment (tools, pre-commit, etc.)
bake assert-setup-dev  # Verify dev environment is properly configured
bake update            # Update dependencies (project + examples + hooks)
```

**Verification workflow:**

1. Make changes
2. Run `bake lint` to check code quality
3. Run `bake test` to verify unit tests pass
4. Commit when both pass

**Development workflow:**

During development, run specific tests instead of the full suite for faster feedback:

```bash
# Run specific test file
uv run pytest tests/unit/bakelib/space/test_space_base.py -v

# Run specific test
uv run pytest tests/unit/bakelib/space/test_space_base.py::test_recipe_with_bakebook_succeeds -v

# Run all tests in a directory
uv run pytest tests/unit/bakelib/ -v
```

**IMPORTANT:** The developer will run `bake test` before committing. During development, only run targeted tests for speed.

**IMPORTANT:** Read `.claude/BEST_PRACTICES.md` before adding/editing code.

**Key Policies:**

- **Docstrings**: Do NOT add docstrings by default. The developer adds them manually when needed. See BEST_PRACTICES.md → "Docstring Policy"
- **No automatic commits**: Do NOT make git commits automatically. The developer will commit when ready.
- **Task-by-task execution**: When working from dev docs task lists, proceed exactly as requested. If user says "1.1" or "Task 1.1", ONLY complete that specific task—do not proceed to other tasks unless explicitly asked. This allows for review and feedback between tasks.

## Pydantic Patterns

Always use the `Annotated` pattern for Pydantic `Field()` configuration:

```python
# ✅ Correct - Annotated pattern
MyFieldType = Annotated[str, Field(min_length=1, max_length=100)]

class MyModel(BaseModel):
    name: MyFieldType

# ❌ Wrong - Field on assignment
class MyModel(BaseModel):
    name: str = Field(min_length=1, max_length=100)
```

## Project Structure

```
src/bake/    # Main package
tests/           # Tests
├── unit/              # Fast unit tests (mocked, no real subprocess)
│   ├── bake/         # Bake-specific tests
│   └── bakelib/      # Bakelib tests
├── integration/      # Slow integration tests (real subprocess, isolated envs)
│   ├── examples/     # Tests against @examples/
│   └── fixtures/     # Tests using temp fixture folders
├── utils/            # Shared test utilities
└── conftest.py       # Shared fixtures
bakefile.py      # Example bakefile
```

## Test Structure

**Unit Tests (`tests/unit/`)** - Fast, isolated tests

- Use mocks to avoid subprocess calls
- Test individual functions and classes in isolation
- Run with `bake test` (completes in ~50 seconds)
- ~1500 tests currently

**Integration Tests (`tests/integration/`)** - Slow, real-world tests

- Run real subprocess commands
- Test against actual examples or temporary projects
- Two categories:
    - `examples/` - Tests against real examples in `@examples/`
    - `fixtures/` - Tests using temporary fixture folders
- Run with `bake test-integration`

**When to write unit vs integration tests:**

- **Unit tests:** Default for new tests. Test logic in isolation with mocks.
- **Integration tests:** Only when testing real subprocess behavior, end-to-end flows, or actual example projects.

**Testing Bakebook subclasses with `mock_ctx`:**

```python
def test_clean_all_runs_git_clean(
    self, mock_ctx: Context, capsys: pytest.CaptureFixture
) -> None:
    clean_utils = CleanUtils()
    with mock_ctx:
        clean_utils.clean_all()
    captured = capsys.readouterr()
    err = strip_ansi(captured.err)
    assert "git clean -fdX" in err
```

- `mock_ctx` is in dry-run mode - commands print to stderr but don't execute
- **Do NOT use `patch` or `mock_result`** - just use `mock_ctx` directly
- Use `strip_ansi()` for colored output
- Check `captured.err` (stderr), not `captured.out`

See `tests/README.md` for detailed testing guidelines.

## Additional Documentation

- `.claude/PROJECT_KNOWLEDGE.md` - Architecture (when project grows)
- `.claude/BEST_PRACTICES.md` - Coding standards (when established)
- `.claude/TROUBLESHOOTING.md` - Common issues
- `.dev/README.md` - Dev docs pattern for complex tasks

## Dev Docs

For complex multi-session tasks, use `.dev/active/` with three-file structure:

- `plan.md` - Strategic plan
- `context.md` - Key decisions & files (update frequently)
- `tasks.md` - Checklist format

**Naming:** `.dev/active/[xx-task-name]/` where `xx` is incremental (01, 02, ...) and `task-name` is a concise kebab-case name.

Use `/dev-docs` command to create these automatically.
