# Context: Bakebook Typer App Migration

## Task Description

Change `bakebook` from `str` to `typer.Typer` to enable subcommand support from user repositories.

**This is Phase 1 (v1) of the bakebook evolution:**

- v0 (current): `bakebook = "some_string"` - placeholder
- v1 (this task): `bakebook = typer.Typer()` - commands only
- v2 (future): `bakebook = Bakebook(commands=..., variables=...)` - full OOP

## Key Design Concepts

### bakefile vs bakebook vs bake

| Term          | Meaning                                                |
| ------------- | ------------------------------------------------------ |
| `bakefile.py` | User's task definition file (like Makefile)            |
| `bakebook`    | Object inside bakefile.py holding commands + variables |
| `bake`        | CLI that loads bakefile.py and runs bakebook commands  |

### Why typer.Typer for bakebook (Phase 1)?

- Enables users to define multiple commands/recipes in their bakefile.py
- Uses familiar typer patterns (same as bake CLI itself)
- Allows proper argument parsing and help generation
- Supports nested subcommands via `typer.Typer()` groups

### Why TypeVar for validate_bakebook?

- Keeps function generic for future type validation needs
- Provides proper type hints: `validate_bakebook(..., expected_type=typer.Typer)` returns `typer.Typer`
- Type checkers (mypy/pyright) understand the return type relationship

### Variable Naming Convention

- Use `bakebook` consistently (NOT `bakebook_app` or other variants)
- This applies to variable names in code, tests, and documentation

## Key Files

### Source Files

- `src/bakefile/cli/bake/main.py` - Entry point, runs the bakebook app
- `src/bakefile/cli/bake/resolve_bakebook.py` - Loads and validates bakebook

### Test Files

- `tests/cli/bake/test_main.py` - Integration tests
- `tests/cli/bake/test_resolve_bakebook.py` - Unit tests
- `tests/conftest.py` - `examples_simple_dir` fixture points to `examples/simple/`

### Example File

- `examples/simple/bakefile.py` - User-facing example

### Documentation Files

- `.claude/PROJECT_KNOWLEDGE.md` - Architecture overview
- `.claude/BEST_PRACTICES.md` - Coding standards + bakebook pattern

## Progress Tracking

See `tasks.md` for current status.
