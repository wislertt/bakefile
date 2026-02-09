# BEST_PRACTICES.md

**Coding standards and patterns for bakefile**

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

### Use the Bakebook Class

The `Bakebook` class (from `bake`) combines Pydantic's `BaseSettings` with Typer's CLI functionality:

```python
from bake import Bakebook

bakebook = Bakebook()
```

---

## Testing Practices

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
chdir_option = ...
file_name_option = ...
...

# ==========================================================
# Bakefile Local CLI Frequently Used Params
# ==========================================================
force_option = ...
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
        _chdir: chdir_option = DEFAULT_CHDIR,
        ...
    ):
        ctx.obj = obj
        show_help_if_no_command(ctx)
    return bake_app_callback
```

---

## Bakebook Pattern

### User's bakefile.py

Users define their bakebook using the `Bakebook` class with commands as methods:

```python
from bake import Bakebook
from bake.ui import console

bakebook = Bakebook()

@bakebook.command()
def build(
    prod: bool = False,
):
    """Build the project."""
    console.success(f"Building{' (prod)' if prod else ''}...")
    # Access context via self.ctx in class-based bakebooks
    # For standalone commands, ctx is available through the command context

@bakebook.command()
def test(
    coverage: bool = False,
):
    """Run tests."""
    console.echo("Running tests...")
    if coverage:
        bakebook.ctx.run("pytest --cov")

@bakebook.command()
def lint():
    """Run linters."""
    console.echo("Running linters...")
    bakebook.ctx.run("ruff check .")
```

### Environment Variables with Bakebook

The `Bakebook` class extends `BaseSettings`, allowing you to define environment variables:

```python
from bake import Bakebook

class MyBakebook(Bakebook):
    # Environment variables (auto-loaded from .env)
    database_url: str
    debug: bool = False
    workers: int = 4

    def get_connection(self):
        return connect(self.database_url)

bakebook = MyBakebook()

# Access env vars directly
url = bakebook.database_url
```

### Class Methods as Commands

Users can define methods as commands with `@bake.command()`:

```python
from bake import Bakebook, command
from bake.ui import console

class MyBakebook(Bakebook):
    database_url: str = "sqlite:///default.db"
    debug: bool = False

    @command()
    def migrate(self):
        """Run migrations - has access to self.database_url and self.ctx"""
        console.echo(f"Migrating {self.database_url}")
        # Use self.ctx to run commands
        self.ctx.run("alembic upgrade head")

    @command(name="deploy-prod")
    def deploy(self):
        """Deploy the application"""
        if self.debug:
            console.echo("Debug mode - skipping deployment")
        else:
            console.echo("Deploying...")
            self.ctx.run("kubectl apply -f deployment.yaml")

    def helper_method(self):
        """Internal helper - NOT a command"""
        return "internal"

bakebook = MyBakebook()
```

**Key points:**

- Methods decorated with `@bake.command()` become CLI commands
- Methods have full access to `self` (instance properties, helper methods)
- Use `self.ctx` to access CLI context (run commands, dry_run mode, verbosity)
- Use `@command(name="custom")` for custom command names
- Undecorated methods remain as helper methods (not exposed as commands)

**Hybrid API:**

Both standalone functions and class methods work:

```python
from bake import Bakebook, command

# Old way: standalone functions (still works)
bakebook = Bakebook()

@bakebook.command()
def standalone_task():
    """This still works - use bakebook.ctx to access context."""
    # Access context via bakebook instance
    bakebook.ctx.run("echo 'Hello'")

# New way: class methods (recommended for context access)
class MyBakebook(Bakebook):
    @command()
    def method_task(self):
        """This is new - use self.ctx for direct context access."""
        # Direct context access via self
        self.ctx.run("echo 'Hello'")
```

### Running Commands

```bash
# List all commands (shows help)
bake -C /path/to/project

# Run a specific command
bake -C /path/to/project build --prod

# With custom bakefile name
bake -f custom_tasks.py test

# With custom bakebook variable name
bake -b my_tasks build
```

### Bakebook Evolution

| Phase        | bakebook Type    | Description                        |
| ------------ | ---------------- | ---------------------------------- |
| v0 (past)    | `str`            | Temporary placeholder              |
| v1 (past)    | `typer.Typer`    | Commands only                      |
| v2 (current) | `Bakebook` class | OOP with commands + env validation |

### Bakebook Class API

The `Bakebook` class combines Pydantic's `BaseSettings` with Typer's CLI functionality.

**Import:**

```python
from bake import Bakebook
```

**Public Methods:**

| Method                     | Purpose                                |
| -------------------------- | -------------------------------------- |
| `command(*args, **kwargs)` | Register commands (delegates to Typer) |

**Environment Variable Configuration:**

The `Bakebook` class uses Pydantic's `SettingsConfigDict`:

```python
model_config = SettingsConfigDict(
    env_file=".env",              # Load from .env file
    env_file_encoding="utf-8",    # File encoding
    extra="ignore"                # Ignore extra fields
)
```

**Environment Variable Priority (highest to lowest):**

1. Keyword arguments: `MyBakebook(database_url="...")`
2. Environment variables: `DATABASE_URL=...`
3. `.env` file values
4. Field defaults

**Type Hints:**

```python
from bake import Bakebook

def process_bakebook(bakebook: Bakebook) -> None:
    """Process a bakebook instance."""
    pass
```

**Public Properties:**

| Property | Purpose                                 |
| -------- | --------------------------------------- |
| `ctx`    | Access CLI context (run, dry_run, etc.) |

### Bakebook Context Property

The `Bakebook` class provides a `.ctx` property that gives commands access to the CLI context. This means you **do NOT need to pass `ctx` as an argument** to your commands.

```python
from bake import Bakebook

class MyBakebook(Bakebook):
    @command()
    def build(self):
        """Build the project - has access to self.ctx"""
        # Run shell commands
        self.ctx.run("cargo build")

        # Check dry_run mode
        if self.ctx.dry_run:
            console.echo("Dry run mode - skipping deployment")

        # Access verbosity level
        if self.ctx.verbosity >= 2:
            console.echo("Verbose output enabled")

bakebook = MyBakebook()
```

**Key points:**

- `self.ctx` is only available within command execution (raises `ContextNotAvailableError` otherwise)
- Access context features: `ctx.run()`, `ctx.dry_run`, `ctx.verbosity`, `ctx.bakebook`
- No need to pass `ctx: Context` as a parameter in your command functions

**Context API:**

```python
# Run commands
self.ctx.run("cargo test")
self.ctx.run("npm install", check=False)

# Dry run mode
if self.ctx.dry_run:
    # Handle dry run behavior
    pass

# Override dry run temporarily
with self.ctx.override_dry_run(True):
    # Commands in this block respect the override
    self.ctx.run("echo 'This is a dry run'")

# Verbosity level
self.ctx.verbosity  # 0=WARNING, 1=INFO, 2=DEBUG
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

## Color Output

### Console Output Pattern

**Use the `console` module from `bakefile.ui` for all user-facing output:**

```python
from bake.ui import console

# Success messages (green, stdout)
console.success("Operation completed")

# Echo messages (plain, stdout, accepts any type)
console.echo("Processing data")
console.echo({"key": "value"})  # prints dict
console.echo(42)  # prints number

# Warning messages (yellow, stderr)
console.warning("File not found")

# Error messages (red, stderr)
console.error("Failed to connect")
```

**Rich Markup in Messages:**

You can use Rich's `[tag]text[/tag]` markup syntax for emphasis:

```python
# Highlight paths or commands
console.error(f"File [bold]{path}[/bold] already exists")
console.info(f"Run [code]bakefile init --inline[/code] to create one")

# Common markup tags
# [bold], [italic], [underline]
# [red], [green], [yellow], [blue], [cyan], [magenta]
# [code] or backticks for monospace
```

**Stream separation:**

- `success()` and `info()` → stdout
- `warning()` and `error()` → stderr

**Type hints:**

- `success(message: str)`, `warning(message: str)`, `error(message: str)` - strings only
- `info(message: Any)` - accepts any object type

### Respect NO_COLOR Environment Variable

The console module automatically handles NO_COLOR:

- Colors enabled: Labels show as "SUCCESS", "WARNING", "ERROR"
- NO_COLOR set: Labels show as "[SUCCESS]", "[WARNING]", "[ERROR]"

```python
# env.py
import os

ENV_NO_COLOR = "NO_COLOR"

def should_use_colors() -> bool:
    value = os.environ.get(ENV_NO_COLOR)
    return value == "" or value is None

# Usage
rich_markup_mode = "rich" if env.should_use_colors() else None
```

---

## Logging

### Verbosity Levels

The bakefile CLI supports three verbosity levels via the `-v` flag:

| Flag   | Level    | Output                        |
| ------ | -------- | ----------------------------- |
| (none) | WARNING+ | Warnings, Errors (default)    |
| `-v`   | INFO+    | Info, Warnings, Errors        |
| `-vv`  | DEBUG+   | Debug, Info, Warnings, Errors |

**Max validation:** `-vvv` raises "Maximum verbosity is -vv" error

### Logging in User Bakefiles

Users can use the standard Python `logging` module in their bakefiles:

```python
# In your bakefile.py
import logging
from bake import Bakebook

bakebook = Bakebook()

@bakebook.command()
def build():
    """Build the project."""
    logging.info("Starting build process...")
    logging.debug("Reading configuration...")
    # ... build logic ...
    logging.info("Build complete!")
```

The logging is automatically intercepted and formatted consistently with the CLI output.

### Internal Logging (for bakefile development)

For internal bakefile CLI development, use `setup_logging()` and Loguru:

```python
from bake.ui import setup_logging
import logging

# Setup with per-module log levels
setup_logging(
    level_per_module={
        "": logging.WARNING,  # Default level
        "bakefile.cli": logging.DEBUG,  # Debug for CLI module
        "bakefile.manage": logging.INFO,  # Info for manage module
    },
    is_pretty_log=True,  # Use human-readable format (False for JSON)
)
```

**Key points:**

- User bakefiles should use `logging` module (standard Python)
- Internal bakefile code uses `setup_logging()` with Loguru
- Standard `logging` calls are intercepted and routed to Loguru for consistent formatting
- Default output is JSON format (`is_pretty_log=False`) for machine parsing
- Use `is_pretty_log=True` for human-readable output in development

---

## CI/CD

### GitHub Actions Cache Key Pattern

**Use a consistent cache key pattern to avoid race conditions and ensure proper cache isolation:**

```
<name>-<job>-<os>-[<matrix>...]-[<dep>...]-<run_id>-<run_attempt>
```

**Cache Key Components:**

| Component       | Purpose                                         | Example                          |
| --------------- | ----------------------------------------------- | -------------------------------- |
| `<name>`        | Identifies what's cached (unique per job)       | `venv`, `deps`, `cargo`          |
| `<job>`         | Isolates caches per job                         | `${{ github.job }}`              |
| `<os>`          | Isolates by operating system                    | `${{ runner.os }}`               |
| `[<matrix>...]` | Isolates by matrix dimensions (optional)        | `py${{ matrix.python-version }}` |
| `[<dep>...]`    | Invalidates when dependencies change (optional) | `${{ hashFiles('uv.lock') }}`    |
| `<run_id>`      | Unique per workflow run                         | `${{ github.run_id }}`           |
| `<run_attempt>` | Unique per retry attempt                        | `${{ github.run_attempt }}`      |

### Single Cache Step (Fast Dependencies)

For dependencies that are quick to reinstall (Python venv, npm):

```yaml
- name: cache-venv
  uses: actions/cache@cdf6c1fa76f9f475f3d7449005a359c84ca0f306 # v5.0.3
  with:
      path: ${{ github.workspace }}/.venv
      key: venv-${{ github.job }}-${{ runner.os }}-py${{ matrix.python-version }}-${{ hashFiles('uv.lock') }}-${{ github.run_id }}-${{ github.run_attempt }}
      restore-keys: |
          venv-${{ github.job }}-${{ runner.os }}-py${{ matrix.python-version }}-${{ hashFiles('uv.lock') }}-${{ github.run_id }}-
          venv-${{ github.job }}-${{ runner.os }}-py${{ matrix.python-version }}-${{ hashFiles('uv.lock') }}-
          venv-${{ github.job }}-${{ runner.os }}-py${{ matrix.python-version }}-
```

### Combined Cache Step (Multiple Related Paths)

For related caches that should be invalidated together:

```yaml
- name: cache-deps
  uses: actions/cache@cdf6c1fa76f9f475f3d7449005a359c84ca0f306 # v5.0.3
  with:
      path: |
          ${{ github.workspace }}/.venv
          ~/.cache/pre-commit
          ~/.cache/ruff
          ~/.bun/install/cache
      key: deps-${{ github.job }}-${{ runner.os }}-py${{ inputs.python_version }}-${{ hashFiles('uv.lock') }}-${{ hashFiles('.pre-commit-config.yaml') }}-${{ github.run_id }}-${{ github.run_attempt }}
      restore-keys: |
          deps-${{ github.job }}-${{ runner.os }}-py${{ inputs.python_version }}-${{ hashFiles('uv.lock') }}-${{ hashFiles('.pre-commit-config.yaml') }}-${{ github.run_id }}-
          deps-${{ github.job }}-${{ runner.os }}-py${{ inputs.python_version }}-${{ hashFiles('uv.lock') }}-${{ hashFiles('.pre-commit-config.yaml') }}-
          deps-${{ github.job }}-${{ runner.os }}-py${{ inputs.python_version }}-${{ hashFiles('uv.lock') }}-
          deps-${{ github.job }}-${{ runner.os }}-py${{ inputs.python_version }}-
```

### Split Restore and Save for Expensive Caches

For caches that are **slow to create** (Rust compilation, large builds), use split restore/save steps to ensure cache is saved even if intermediate steps fail:

```yaml
jobs:
    build:
        # Define cache path as env var to avoid redundancy
        env:
            CARGO_CACHE_PATH: |
                ~/.cargo/registry
                ~/.cargo/git
                target

        steps:
            # 1. Restore cache (fails gracefully if not found)
            - name: restore-cargo-cache
              id: restore-cargo
              uses: actions/cache/restore@0c907a7517f239e4053e11f1aee0df0fd0823747 # v4.2.1
              with:
                  path: ${{ env.CARGO_CACHE_PATH }}
                  key: cargo-${{ github.job }}-${{ runner.os }}-${{ hashFiles('**/Cargo.lock') }}-${{ github.run_id }}-${{ github.run_attempt }}
                  restore-keys: |
                      cargo-${{ github.job }}-${{ runner.os }}-${{ hashFiles('**/Cargo.lock') }}-

            # 2. Build step (may fail, but cache will still be saved)
            - name: build
              run: cargo build --release

            # 3. Save cache (runs even if build fails)
            - name: save-cargo-cache
              if: always()
              uses: actions/cache/save@8c838cbe8e9c4b41d7be8ca7bcc388df19aa43b1 # v4.2.1
              with:
                  path: ${{ env.CARGO_CACHE_PATH }}
                  key: ${{ steps.restore-cargo.outputs.cache-primary-key }}
```

**When to use split restore/save:**

| Cache Type   | Use Split? | Reason                                           |
| ------------ | ---------- | ------------------------------------------------ |
| Rust cargo   | ✅ Yes     | Compilation is expensive - save partial progress |
| Large builds | ✅ Yes     | Don't waste hours of build time                  |
| Python venv  | ❌ No      | `uv sync` is fast enough                         |
| npm deps     | ❌ No      | `npm install` is relatively fast                 |

### Cache Step Placement

**Correct order for cache steps:**

```yaml
steps:
    # 1. ALWAYS FIRST - Need code to know what to cache
    - name: checkout
      uses: actions/checkout@...

    # 2. Tool setup with built-in caching
    - name: setup-uv
      uses: astral-sh/setup-uv@...
      with:
          enable-cache: true # Handles ~/.cache/uv

    # 3. YOUR cache - Restore if exists
    - name: cache-deps
      uses: actions/cache@...
      with:
          path: .venv
          key: ...

    # 4. Install - Uses cache if available, creates if not
    - name: install-dependencies
      run: uv sync --all-extras --all-groups --frozen
```

### Naming Convention

Keep step name and cache prefix consistent:

| Step Name     | Key Prefix |
| ------------- | ---------- |
| `cache-venv`  | `venv-`    |
| `cache-deps`  | `deps-`    |
| `cache-cargo` | `cargo-`   |

### Key points:

- Use **full commit SHA** (not `@v4`) for security - version tags can move
- Each cache in a job must have a unique `<name>` to avoid collisions
- `run_id` + `run_attempt` ensure cache can be saved after every run (no cross-run exact hits)
- `restore-keys` provide fallback to older caches by removing elements from the back
- Multiple caches per job are allowed and recommended for different purposes
- For split pattern: use `if: always()` on save step, reference `steps.<id>.outputs.cache-primary-key`
- Use `env:` variables for cache paths to avoid redundancy in split restore/save
- The `id:` field cannot use expressions - must be static strings
