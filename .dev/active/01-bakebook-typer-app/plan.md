# Plan: Change bakebook from str to typer.Typer

## Goal

Enable `bakebook` in user's `bakefile.py` to be a `typer.Typer` app instead of a `str`, so it can run as a subcommand with full CLI capabilities.

## Current State

```python
# In user's bakefile.py
bakebook = "some_bakebook"  # Just a string
```

```python
# resolve_bakebook.py - returns str
def resolve_bakebook(file_name: str, bakebook_name: str, chdir: str | None = None) -> str:
    ...
    return get_bakebook(module=module, bakebook_name=bakebook_name, path=path)

def validate_bakebook(bakebook: Any, bakebook_name: str, expected_type: type) -> str:
    if not isinstance(bakebook, expected_type):
        typer.echo(...)
        raise SystemExit(1)
    return bakebook
```

```python
# main.py - just echoes string
@app.command()
def main(...) -> None:
    bakebook = resolve_bakebook(...)
    typer.echo(bakebook)  # Just prints string
```

## Target State

```python
# In user's bakefile.py
import typer

bakebook = typer.Typer()

@bakebook.command()
def hello(name: str = "world"):
    typer.echo(f"Hello {name}!")

@bakebook.command()
def build():
    typer.echo("Building...")
```

```python
# resolve_bakebook.py - returns typer.Typer, with generic TypeVar for type safety
from typing import TypeVar

T = TypeVar("T")

def resolve_bakebook(file_name: str, bakebook_name: str, chdir: str | None = None) -> typer.Typer:
    ...
    return get_bakebook(module=module, bakebook_name=bakebook_name, path=path)

def validate_bakebook(bakebook: Any, bakebook_name: str, expected_type: type[T]) -> T:
    """Validate bakebook is of expected type and return it.

    Uses TypeVar for proper type inference - when called with
    expected_type=typer.Typer, the return type is typer.Typer.
    """
    if not isinstance(bakebook, expected_type):
        typer.echo(
            f"Bakebook '{bakebook_name}' must be a {expected_type.__name__}, "
            f"got {type(bakebook).__name__}",
            err=True,
        )
        raise SystemExit(1)
    return bakebook
```

```python
# main.py - runs the typer app
@app.command(context_settings={"ignore_unknown_options": True})
def main(
    ctx: typer.Context,
    chdir: str = typer.Option(None, "-C", "--chdir", help="Change directory before running"),
    file_name: str = typer.Option("bakefile.py", "--file-name", "-f", help="Path to bakefile.py"),
    bakebook_name: str = typer.Option(
        "bakebook", "--book-name", "-b", help="Name of bakebook object to retrieve"
    ),
    version: bool = typer.Option(
        False,
        "--version",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    bakebook = resolve_bakebook(file_name=file_name, bakebook_name=bakebook_name, chdir=chdir)
    # Pass remaining args to the bakebook
    bakebook(args=ctx.args if ctx.args else ["--help"])
```

## Implementation Steps

### 1. Update `src/bakefile/cli/bake/resolve_bakebook.py`

Changes:

- Add `from typing import TypeVar` and define `T = TypeVar("T")`
- Update `validate_bakebook()` signature to use `expected_type: type[T]` -> `T` for generic type inference
- Add docstring to `validate_bakebook()` explaining TypeVar usage
- Update `get_bakebook()` to pass `typer.Typer` as expected type
- Update `get_bakebook()` return type to `typer.Typer`
- Update `resolve_bakebook()` return type to `typer.Typer`

### 2. Update `src/bakefile/cli/bake/main.py`

Changes:

- Add `context_settings={"ignore_unknown_options": True}` to capture unknown args
- Add `ctx: typer.Context` parameter to access remaining args
- Change `typer.echo(bakebook)` to run the retrieved typer app
- Pass remaining args to the bakebook (use variable name `bakebook`, NOT `bakebook_app`)

### 3. Update `examples/simple/bakefile.py`

Changes:

- Import `typer`
- Create `bakebook = typer.Typer()`
- Add example commands to the bakebook

### 4. Update `tests/cli/bake/test_resolve_bakebook.py`

Changes:

- Update `test_get_bakebook_valid_string` to `test_get_bakebook_valid_typer`
- Create mock typer.Typer app instead of string
- Update `test_resolve_bakebook_with_chdir` expectation
- Update `test_resolve_bakebook_without_chdir` expectation
- Update `test_get_bakebook_not_string` to `test_get_bakebook_not_typer`

### 5. Update `tests/cli/bake/test_main.py`

Changes:

- Update `test_bake_with_chdir` to expect help output (default behavior with no args)
- Or pass a command and test actual execution

### 6. Update `.claude/BEST_PRACTICES.md`

Add new section documenting the bakebook pattern:

````markdown
## Bakebook Pattern

### User's bakefile.py

Users should define their bakebook as a `typer.Typer` app:

```python
import typer

bakebook = typer.Typer()

@bakebook.command()
def build(
    prod: bool = typer.Option(False, "--prod", help="Production build"),
):
    \"\"\"Build the project.\"\"\"
    typer.echo(f"Building{' (prod)' if prod else ''}...")

@bakebook.command()
def test():
    \"\"\"Run tests.\"\"\"
    typer.echo("Running tests...")
```
````

### Running Commands

```bash
# List all commands
bake -C /path/to/project

# Run a specific command
bake -C /path/to/project build --prod

# With custom bakefile
bake -f custom_tasks.py test
```

```

## Files to Modify

1. `src/bakefile/cli/bake/resolve_bakebook.py`
2. `src/bakefile/cli/bake/main.py`
3. `examples/simple/bakefile.py`
4. `tests/cli/bake/test_resolve_bakebook.py`
5. `tests/cli/bake/test_main.py`
6. `.claude/BEST_PRACTICES.md`

## Verification

After implementation:
1. Run `make lint` to verify code quality
2. Run `make test` to verify all tests pass
3. Manually test `bake -C examples/simple build`
```
