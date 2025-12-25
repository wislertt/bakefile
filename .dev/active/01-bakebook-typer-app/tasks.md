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

- [ ] Update `src/bakefile/cli/bake/resolve_bakebook.py`
    - [ ] Add `from typing import TypeVar` and define `T = TypeVar("T")`
    - [ ] Update `validate_bakebook(expected_type: type[T]) -> T` for generic type inference
    - [ ] Add docstring explaining TypeVar usage
    - [ ] Update return types to `typer.Typer`

- [ ] Update `src/bakefile/cli/bake/main.py`
    - [ ] Add `context_settings={"ignore_unknown_options": True}` to main command
    - [ ] Add `ctx: typer.Context` parameter
    - [ ] Replace `typer.echo(bakebook)` with app execution
    - [ ] Forward remaining args to `bakebook` (NOT `bakebook_app`)

### Example

- [ ] Update `examples/simple/bakefile.py`
    - [ ] Import `typer`
    - [ ] Create `bakebook = typer.Typer()`
    - [ ] Add example commands (e.g., `hello`, `build`)

### Tests

- [ ] Update `tests/cli/bake/test_resolve_bakebook.py`
    - [ ] Update `test_get_bakebook_valid_string` → `test_get_bakebook_valid_typer`
    - [ ] Create mock typer.Typer instead of string
    - [ ] Update `test_resolve_bakebook_with_chdir` expectations
    - [ ] Update `test_resolve_bakebook_without_chdir` expectations
    - [ ] Update `test_get_bakebook_not_string` → `test_get_bakebook_not_typer`

- [ ] Update `tests/cli/bake/test_main.py`
    - [ ] Update `test_bake_with_chdir` for new output behavior

## Verification

- [ ] Run `make lint` - all checks pass
- [ ] Run `make test` - all tests pass
- [ ] Manual test: `bake -C examples/simple` shows help
- [ ] Manual test: `bake -C examples/simple hello --name=Claude` works
