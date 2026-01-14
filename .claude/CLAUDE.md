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
make test   # Run tests with coverage
make lint   # Run linters and formatters
```

**Verification workflow:**

1. Make changes
2. Run `make lint` to check code quality
3. Run `make test` to verify tests pass
4. Commit when both pass

**Development workflow:**

During development, run specific tests instead of the full suite for faster feedback:

```bash
# Run specific test file
uv run pytest tests/bakelib/space/test_space_base.py -v

# Run specific test
uv run pytest tests/bakelib/space/test_space_base.py::test_recipe_with_bakebook_succeeds -v

# Run all tests in a directory
uv run pytest tests/bakelib/ -v
```

**IMPORTANT:** The developer will run `make test` before committing. During development, only run targeted tests for speed.

**IMPORTANT:** Read `.claude/BEST_PRACTICES.md` before adding/editing code.

**Key Policies:**

- **Docstrings**: Do NOT add docstrings by default. The developer adds them manually when needed. See BEST_PRACTICES.md → "Docstring Policy"
- **No automatic commits**: Do NOT make git commits automatically. The developer will commit when ready.

## Project Structure

```
src/bake/    # Main package
tests/           # Tests
bakefile.py      # Example bakefile
```

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
