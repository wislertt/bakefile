# CODING_STANDARDS.md

**Coding standards for bakefile, enforced in review**

## Naming Conventions

### bakebook Variable Name

**Always use `bakebook` (not `bakebook_app`, `bakebook_cli`, etc.)**

This applies consistently across:

- User's `bakefile.py`
- Internal variable names in `bake` CLI
- Test files
- Documentation

```python
# Good
from bake import Bakebook

bakebook = Bakebook()

# Bad
bakebook_app = Bakebook()
bakebook_cli = Bakebook()
```

### Variable Naming Patterns

- Use trailing underscores for parameters that shadow built-ins or have naming conflicts
- Use `_` prefix for intentionally unused variables

```python
# From app.py
def bake_app_callback(
    ctx: Context,
    _chdir: chdir_option = DEFAULT_CHDIR,
    _file_name: file_name_option = DEFAULT_FILE_NAME,
    _bakebook_name: bakebook_name_option = DEFAULT_BAKEBOOK_NAME,
    _version: version_option = False,
    _is_chain_commands: is_chain_commands_option = None,
):
    ctx.obj = obj
    show_help_if_no_command(ctx)
```

---

## Documentation

### Docstring Policy

**DO NOT add docstrings by default. Docstrings are added manually by the developer when needed.**

When implementing code or refactoring:

- ❌ **Do NOT** add docstrings automatically
- ❌ **Do NOT** add placeholder docstrings like `"""TODO: add docstring"""`
- ✅ The developer will add docstrings manually when they deem it necessary

**The developer adds docstrings for:**

- Public API functions that need usage documentation
- Complex functions with non-obvious behavior
- Functions with multiple parameters requiring explanation
- Functions that raise specific exceptions worth documenting

**Skip docstrings for:**

- Simple functions with self-explanatory names
- Internal/private functions
- Functions where the type hints and parameter names are sufficient
- `__init__.py` files

### Docstring Format (when added manually)

**Use NumPy format for multi-line docstrings:**

```python
from typing import TypeVar

T = TypeVar("T")


def validate_value(value: Any, expected_type: type[T]) -> T:
    """Validate that value matches expected type.

    Parameters
    ----------
    value : Any
        The value to validate
    expected_type : type[T]
        The expected type to check against

    Returns
    -------
    T
        The validated value

    Raises
    ------
    SystemExit
        If validation fails
    """
```

---

## Type Annotations

### Use Annotated Types for CLI Parameters

Define reusable CLI parameters using `Annotated` types in `params.py`:

```python
from pathlib import Path
from typing import Annotated
import typer

chdir_option = Annotated[
    Path,
    typer.Option(
        "-C",
        "--chdir",
        help="Change directory before running",
    ),
]

file_name_option = Annotated[
    str,
    typer.Option(
        "--file-name",
        "-f",
        help="Path to bakefile.py",
        callback=validate_file_name_callback,
    ),
]
```

### Use Annotated for Pydantic Field Configuration

Put `Field()` inside `Annotated`, not on the assignment:

```python
# ✅ Correct
MyFieldType = Annotated[str, Field(min_length=1, max_length=100)]


class MyModel(BaseModel):
    name: MyFieldType


# ❌ Wrong
class MyModel(BaseModel):
    name: str = Field(min_length=1, max_length=100)
```

### Use the Bakebook Class

The `Bakebook` class (from `bake`) combines Pydantic's `BaseSettings` with Typer's CLI functionality:

```python
from bake import Bakebook

bakebook = Bakebook()
```

---

## Testing Practices

### Use mock_ctx Instead of Patches

**When testing with `mock_ctx` fixture, avoid using `patch` or `mock` unless absolutely necessary.**

The `mock_ctx` fixture provides a dry-run context where commands are printed to stderr instead of being executed. This means you can verify behavior by checking the captured output, without needing to patch internal functions.

**❌ Bad - Over-using patches:**

```python
def test_setup_tools_calls_sync_submodules_frozen(self, mock_ctx: Context) -> None:
    utils = SubmodulesUtils()
    run_calls: list[str] = []

    def capture_run(cmd: str, **_: object) -> MagicMock:
        run_calls.append(cmd)
        mock_result = MagicMock()
        mock_result.stdout = "{}"
        return mock_result

    with (
        mock_ctx,
        patch.object(mock_ctx, "run", side_effect=capture_run),
        patch("bakelib.space.base.install_mise_tools"),
    ):
        utils.setup_tools()

    submodule_calls = [c for c in run_calls if "submodule" in c]
    assert len(submodule_calls) == 1
```

**✅ Good - Just check captured stderr:**

```python
def test_setup_tools_calls_sync_submodules_frozen(
    self, mock_ctx: Context, capsys: pytest.CaptureFixture
) -> None:
    utils = SubmodulesUtils()
    with mock_ctx:
        utils.setup_tools()
    captured = capsys.readouterr()
    err = strip_ansi(captured.err)
    assert "git submodule update --init --recursive" in err
    assert "--remote" not in err
```

**When patches ARE appropriate:**

- Testing error handling that would otherwise terminate the test
- Mocking external services or APIs
- Isolating specific functionality with complex dependencies
- When you need to verify internal state changes without side effects

**When patches are NOT needed:**

- Verifying what commands would be run (dry-run mode shows this)
- Testing command execution order (captured output shows this)
- Simple behavior verification that outputs to stderr/stdout

### Test Folder Structure

Tests mirror the source folder structure for easy navigation and maintainability.

**Example:**

```
src/bake/cli/common/  tests/cli/common/
├── __init__.py          ├── __init__.py
├── app.py               ├── test_app.py
├── callback.py          ├── test_callback.py
├── context.py           ├── test_context.py
└── obj.py               └── test_obj.py
```

**Rules:**

- Create corresponding test file in `tests/` for each module in `src/`
- Use `test_` prefix for test files
- Maintain same directory hierarchy
- Each test file should test its corresponding source module

---

## Code Organization

### File Structure Patterns

#### Group related functionality with separator comments

```python
# params.py

# ==========================================================
# Bakefile CLI Parameters
# ==========================================================
ChdirOption = ...
FileNameOption = ...
...

# ==========================================================
# Bakefile Local CLI Frequently Used Params
# ==========================================================
ForceOption = ...
```

#### Keep **init**.py minimal

Only export what's necessary, prefer explicit imports:

```python
# __init__.py
from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]


def _get_version() -> str:
    try:
        return version("bake")
    except PackageNotFoundError:
        return "0.0.0"


__version__ = _get_version()
```

---

## Error Handling

### Custom Exception Hierarchy

Define a base exception for all project-specific exceptions:

```python
# exceptions.py
class BaseBakefileError(Exception):
    """Base exception for all bakefile errors."""


class BakebookError(BaseBakefileError):
    """Exception raised when bakebook cannot be loaded or validated."""
```

### Use contextlib.suppress for Graceful Degradation

```python
# obj.py
import contextlib


def get_bakebook(self):
    if self.bakebook is not None:
        return

    with contextlib.suppress(BakebookError):
        self.bakefile_path = resolve_bakefile_path(...)
        self.bakebook = get_bakebook_from_target_dir_path(...)
```

### Use Typer's BadParameter for Input Validation

```python
# callback.py
import typer


def validate_file_name(file_name: str) -> str:
    if "/" in file_name or "\\" in file_name:
        raise typer.BadParameter(f"File name must not contain path separators: {file_name}")
    if not file_name.endswith(".py"):
        raise typer.BadParameter(f"File name must end with .py: {file_name}")
    return file_name
```

---

## Dataclass Patterns

### Use dataclasses for Configuration Objects

```python
@dataclass
class BakefileObject:
    chdir: Path
    file_name: str
    bakebook_name: str
    bakefile_path: Path | None = None
    bakebook: Bakebook | None = None

    def __post_init__(self):
        validate_file_name(self.file_name)
```

---

## CLI Patterns

### Context Subclass for Type Safety

Create a typed `Context` subclass to pass objects through CLI:

```python
# context.py
import typer
from .obj import BakefileObject


class Context(typer.Context):
    obj: BakefileObject
```

### Show Help When No Command Invoked

```python
# app.py
def show_help_if_no_command(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
```

### Use Callback to Set Context Object

```python
def bake_app_callback_with_obj(obj: BakefileObject) -> Callable:
    def bake_app_callback(
        ctx: Context,
        _chdir: ChdirOption = DEFAULT_CHDIR,
        ...
    ):
        ctx.obj = obj
        show_help_if_no_command(ctx)
    return bake_app_callback
```

---

## Constants

### Define Constants in Dedicated Module

```python
# constants.py
from pathlib import Path

# Default value
DEFAULT_CHDIR = Path(".")
DEFAULT_FILE_NAME = "bakefile.py"
DEFAULT_BAKEBOOK_NAME = "bakebook"

# Bakefile app command name
GET_BAKEFILE_OBJECT = "get_bakefile_object"

# Others
BAKEBOOK_NAME_IN_SAMPLES = "__bakebook__"
```

---

## Reference

Read the matching file when working in that area:

- Bakebook class, commands, env vars, context: `src/bake/bakebook/README.md`
- `console` output helpers and colors: `src/bake/ui/README.md`
- Verbosity and logging config (user-facing: `docs/usage/logging.mdx`): `src/bake/ui/logger/README.md`
- GitHub Actions caching: `CONTRIBUTING.md`
