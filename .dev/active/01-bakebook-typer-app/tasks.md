# Tasks: Bakebook Typer App Migration

## Implementation Checklist

**Note:** Documentation updates are done first to establish patterns before code changes.

### Documentation (Do First)

- [x] Update `.claude/PROJECT_KNOWLEDGE.md` with bakefile architecture
- [x] Update `.dev/active/01-bakebook-typer-app/context.md` with correct design
- [x] Update `.dev/active/01-bakebook-typer-app/plan.md` with variable naming convention
- [x] Update `.claude/BEST_PRACTICES.md`
    - [x] Add "Naming Conventions" section (bakebook variable name)
    - [x] Add "Bakebook Pattern" section with usage examples
    - [x] Update docstring example to generic `validate_value`

### Source Code

- [x] Update `src/bakefile/cli/bake/resolve_bakebook.py`
    - [x] Add `from typing import TypeVar` and define `T = TypeVar("T")`
    - [x] Update `validate_bakebook(expected_type: type[T]) -> T` for generic type inference
    - [x] Add docstring explaining TypeVar usage
    - [x] Update return types to `typer.Typer`

- [x] Update `src/bakefile/cli/bake/main.py`
    - [x] Add `context_settings={"allow_extra_args": True, "allow_interspersed_args": False}`
    - [x] Add `ctx: typer.Context` parameter
    - [x] Replace `typer.echo(bakebook)` with app execution
    - [x] Forward remaining args to `bakebook` (NOT `bakebook_app`)

### Example

- [x] Update `examples/simple/bakefile.py`
    - [x] Import `typer`
    - [x] Create `bakebook = typer.Typer()`
    - [x] Add example commands (e.g., `hello`, `build`)

### Tests

- [x] Update `tests/cli/bake/test_resolve_bakebook.py`
    - [x] Update `test_get_bakebook_valid_string` → `test_get_bakebook_valid_typer`
    - [x] Create mock typer.Typer instead of string
    - [x] Update `test_resolve_bakebook_with_chdir` expectations
    - [x] Update `test_resolve_bakebook_without_chdir` expectations
    - [x] Update `test_get_bakebook_not_string` → `test_get_bakebook_not_typer`

- [x] Update `tests/cli/bake/test_main.py`
    - [x] Update `test_bake_with_chdir` for new output behavior
    - [x] Add `test_bake_with_chdir_runs_command` for actual command execution

## Verification

- [x] Run `make lint` - all checks pass
- [x] Run `make test` - all tests pass (28/28, 100% coverage)
- [x] Manual test: `bake -C examples/simple` shows help
- [x] Manual test: `bake -C examples/simple hello --name=Claude` works

## Summary

**Phase 1 (v1) of bakebook evolution is complete!**

The `bakebook` is now a `typer.Typer` app that supports:

- Multiple commands as subcommands
- Proper argument parsing and help generation
- Nested subcommands via `typer.Typer()` groups

**Next phase (v2):** Add Pydantic model for variables/config (OOP reusability)
