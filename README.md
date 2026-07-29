[![tests](https://img.shields.io/github/actions/workflow/status/wislertt/bakefile/cd.yml?branch=main&label=tests&logo=github)](https://github.com/wislertt/bakefile/actions/workflows/cd.yml)
[![release](https://img.shields.io/github/actions/workflow/status/wislertt/bakefile/cd.yml?branch=main&label=release&logo=github)](https://github.com/wislertt/bakefile/actions/workflows/cd.yml)
[![quality-gate-status](https://sonarcloud.io/api/project_badges/measure?project=wislertt_bakefile&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=wislertt_bakefile)
[![security-rating](https://sonarcloud.io/api/project_badges/measure?project=wislertt_bakefile&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=wislertt_bakefile)
[![vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=wislertt_bakefile&metric=vulnerabilities)](https://sonarcloud.io/summary/new_code?id=wislertt_bakefile)
[![codecov](https://codecov.io/gh/wislertt/bakefile/graph/badge.svg?token=G0ZRDBGAJB)](https://codecov.io/gh/wislertt/bakefile)
[![pypi](https://img.shields.io/pypi/v/bakefile.svg?color=blue)](https://pypi.python.org/pypi/bakefile)
[![downloads](https://static.pepy.tech/personalized-badge/bakefile?period=total&units=international_system&left_color=grey&right_color=blue&left_text=pypi%20downloads)](https://pepy.tech/projects/bakefile)
[![python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue?logo=python)](https://github.com/wislertt/bakefile/)

# bakefile

An OOP task runner in Python. Like a Makefile, but with tasks as Python class methods—so you can inherit, compose, and reuse them across projects.

## Why bakefile?

- **Reusable** - Makefile/Justfile work well, but reusing tasks across projects is hard. bakefile uses OOP class methods—inherit, compose, and share them
- **Python** - Use Python instead of DSL syntax. Access the full ecosystem with Python's language features, tooling, and type safety (ruff/ty)—with subprocess support for normal CLI commands
- **Language-agnostic** - Write tasks in Python, run commands for any language (Go, Rust, JS, etc.)

## Installation

Install via pip:

```bash
pip install bakefile
```

Or via uv:

```bash
uv add bakefile          # as a project dependency
uv tool install bakefile # as a global tool
```

## Quick Start

Create a file named `bakefile.py`:

```python
from bake import Bakebook, command, console


class MyBakebook(Bakebook):
    @command()
    def build(self) -> None:
        console.echo("Building...")
        # Use self.ctx to run commands
        self.ctx.run("cargo build")


bakebook = MyBakebook()


@bakebook.command()
def hello(name: str = "world"):
    console.echo(f"Hello {name}!")
```

**Tip:** Or generate a bakefile automatically:

```bash
bakefile init           # Basic bakefile
bakefile init --inline  # With PEP 723 standalone dependencies
```

Run your tasks:

```bash
bake hello              # Hello world!
bake hello --name Alice # Hello Alice!
bake build              # Building...
```

## Core Concepts

### Two CLIs

bakefile provides two command-line tools:

- **`bake`** - Runs tasks from your `bakefile.py`
- **`bakefile`** - Manages your `bakefile.py` (init, add-inline, lint, find-python, export, sync, lock, add, pip)

Detailed CLI documentation in [Usage](#usage).

### Bakebook

A class in `bakefile.py` that holds your tasks:

- **Inherit and reuse** - Create base classes with common tasks, extend them across projects
- **Extends Pydantic's `BaseSettings`** - Define configuration as class attributes
- **Uses `@command()` decorator** - Same syntax as Typer for defining CLI commands
- **Provides `ctx.run()`** - Execute CLI commands (built on Python's subprocess) from your tasks

```python
from bake import Bakebook, command, Context, console
from pydantic import Field
from typing import Annotated
import typer


class MyBakebook(Bakebook):
    # Pydantic configuration
    api_url: str = Field(default="https://api.example.com", env="API_URL")

    @command()
    def fetch(self) -> None:
        # Run CLI commands via self.ctx
        self.ctx.run(f"curl {self.api_url}")


bakebook = MyBakebook()


# Standalone functions also work
@bakebook.command()
def test(
    verbose: Annotated[bool, typer.Option(False, "--verbose", "-v")] = False,
):
    if verbose:
        console.echo("Running tests...")
    bakebook.ctx.run("pytest")
```

### PEP 723 Support

bakefile supports [PEP 723](https://peps.python.org/pep-0723/) inline script metadata—your `bakefile.py` can declare its own dependencies. Add PEP 723 metadata to an existing bakefile with `bakefile add-inline`:

```python
# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "bakefile>=0.0.0",
# ]
# ///

from bake import Bakebook, command, console

bakebook = Bakebook()


@bakebook.command()
def hello():
    console.echo("Hello from standalone bakefile!")
```

**Use case:** Ideal for non-Python projects without `pyproject.toml`. For Python projects, add bakefile to your project's dependencies instead.

## Usage

### Bakebook API

#### Creating a Bakebook

**Tip:** Generate a bakefile automatically with `bakefile init` or `bakefile add-inline`.

Create a bakebook by inheriting from `Bakebook` or instantiating it:

```python
from bake import Bakebook

bakebook = Bakebook()
```

#### @command Decorator

- **Pattern 1: Before instantiating** - Use `@command()` on class methods
- **Pattern 2: After instantiating** - Use `@bakebook.command()` on standalone functions
- **Accepts all Typer options** - `name`, `help`, `deprecated`, etc.

```python
from bake import Bakebook, command, console
from typing import Annotated
import typer


# Pattern 1: On class (use self.ctx for context access)
class MyBakebook(Bakebook):
    @command()
    def task1(self) -> None:
        console.echo("Task 1")
        self.ctx.run("echo 'Task 1 complete'")


bakebook = MyBakebook()


# Pattern 2: On instance (use bakebook.ctx for context access)
@bakebook.command(name="deploy", help="Deploy application")
def deploy(
    env: Annotated[str, typer.Option("dev", help="Environment to deploy")],
):
    console.echo(f"Deploying to {env}...")
    bakebook.ctx.run(f"kubectl apply -f {env}.yaml")
```

#### Context API

The `Bakebook` class provides a `.ctx` property for accessing CLI context:

```python
class MyBakebook(Bakebook):
    @command()
    def my_command(self) -> None:
        # Run a command
        self.ctx.run("echo hello")

        # Run with options
        self.ctx.run(
            "pytest",
            capture_output=False,  # Stream to terminal
            check=True,  # Raise on error
            cwd="/tmp",  # Working directory
            env={"KEY": "value"},  # Environment variables
        )

        # Run a multi-line script
        self.ctx.run_script(
            title="Setup",
            script="""
                echo "Step 1"
                echo "Step 2"
            """,
        )
```

#### Pydantic Settings

Bakebooks extend Pydantic's `BaseSettings` for configuration:

```python
from bake import Bakebook
from pydantic import Field


class MyBakebook(Bakebook):
    # Defaults
    database_url: str = "sqlite:///db.sqlite3"

    # With environment variable mapping
    api_key: str = Field(default="default-key", env="API_KEY")

    # With validation
    port: int = Field(default=8000, ge=1, le=65535)
```

Settings are loaded from environment variables, `.env` files, or defaults.

### `bake` CLI - Running Tasks

The `bake` command runs tasks from your `bakefile.py`. Run `bake --help` to see all available commands and options.

#### Basic Execution

```bash
bake <command> [args]
```

```bash
bake hello
bake build
bake test --verbose
```

#### Dry-Run Mode

Preview what would happen without executing:

```bash
bake -n build
bake --dry-run deploy
```

#### Verbosity Levels

Control output verbosity:

```bash
bake build              # Silent (errors only)
bake -v build           # Info level
bake -vv build          # Debug level
```

#### Chaining Commands

Run multiple commands sequentially:

```bash
bake -c lint test build
```

If any command fails, the chain stops.

#### Options

Override defaults when running bake:

```bash
bake -f tasks.py build                   # Custom filename
bake -b my_bakebook build                # Custom bakebook object name
bake -C /path/to/project build           # Run from different directory
```

### `bakefile` CLI - Managing bakefile.py

The `bakefile` command (short: `bf`) manages your `bakefile.py`.

#### init

Create a new `bakefile.py`:

```bash
bakefile init           # Basic bakefile
bakefile init --inline  # With PEP 723 inline metadata
bakefile init --force   # Force overwrite existing bakefile
```

#### add-inline

Add PEP 723 inline metadata to an existing bakefile:

```bash
bakefile add-inline
```

#### lint

Lint `bakefile.py` (or entire project) with ruff and ty:

```bash
bakefile lint                   # Lint bakefile.py and all Python files
bakefile lint --only-bakefile   # Lint only bakefile.py
bakefile lint --no-ty           # Skip type checking
```

#### uv-based commands (PEP 723 bakefile.py only)

Convenience wrappers around `uv` commands with `--script bakefile.py` added. For PEP 723 bakefile.py files only. For normal Python projects, use your preferred dependency manager (pip, poetry, uv, etc.).

```bash
bakefile sync                   # = uv sync --script bakefile.py
bakefile lock                   # = uv lock --script bakefile.py
bakefile add requests           # = uv add --script bakefile.py requests
bakefile pip install            # = uv pip install --python <bakefile-python-path>
```

#### find-python

Find the Python interpreter path for the bakefile:

```bash
bakefile find-python
```

#### export

Export bakebook variables to external formats:

```bash
bakefile export                     # Shell format (default)
bakefile export -f sh               # Shell format
bakefile export -f dotenv           # .env format
bakefile export -f json             # JSON format
bakefile export -f yaml             # YAML format
bakefile export -o config.sh        # Write to file

# Examples:
bakefile export -f dotenv -o .env       # .env file
bakefile export -f json -o config.json  # JSON file
```

### `bakelib` - Optional Helpers

**bakelib** is an optional collection of opinionated helpers built on top of Bakebook. Includes Spaces (pre-configured tasks) and Environ (multi-environment support).

Install with:

```bash
pip install bakefile[lib]
```

**Note:** bakelib is optional—you can use bakefile without it. Create your own Bakebook classes if you prefer different conventions.

#### PythonSpace

PythonSpace provides common tasks for Python projects:

```python
from bakelib import PythonSpace

bakebook = PythonSpace()
```

Available commands:

- `bake lint` - Run prettier, toml-sort, ruff format, ruff check, ty, deptry
- `bake test` - Run pytest with coverage on `tests/unit/`
- `bake test-integration` - Run integration tests from `tests/integration/`
- `bake test-all` - Run all tests
- `bake clean` - Clean gitignored files (with exclusions)
- `bake clean-all` - Clean all gitignored files
- `bake setup-dev` - Setup Python development environment
- `bake tools` - List development tools
- `bake update` - Upgrade dependencies (includes uv lock --upgrade)

#### Creating Custom Spaces

Create custom spaces by inheriting from BaseSpace:

```python
from bakelib import BaseSpace


class MySpace(BaseSpace):
    def test(self) -> None:
        self.ctx.run("npm test")


bakebook = MySpace()
```

BaseSpace provides these tasks (override as needed):

- `lint()` - Run prettier
- `clean()` / `clean_all()` - Clean gitignored files
- `setup_dev()` - Setup development environment
- `tools()` - List development tools
- `update()` - Upgrade dependencies

#### Multi-Environment Bakebooks

For projects with multiple environments (dev, staging, prod), use environment mixins:

```python
from bakelib.environ import (
    BaseEnv,
    DevEnvMixin,
    EnvBakebook,
    ProdEnvMixin,
    StagingEnvMixin,
    get_bakebook,
)


# Compose env mixins with EnvBakebook
class DevBakebook(DevEnvMixin, EnvBakebook[BaseEnv]):
    pass


class StagingBakebook(StagingEnvMixin, EnvBakebook[BaseEnv]):
    pass


class ProdBakebook(ProdEnvMixin, EnvBakebook[BaseEnv]):
    pass


bakebook_dev = DevBakebook()
bakebook_staging = StagingBakebook()
bakebook_prod = ProdBakebook()

# Select bakebook based on ENV environment variable
bakebook = get_bakebook([bakebook_dev, bakebook_staging, bakebook_prod])
```

```bash
ENV=prod bake deploy    # Uses prod bakebook
ENV=dev bake deploy     # Uses dev bakebook
bake deploy             # Defaults to dev (lowest priority)
```

Create custom environments by inheriting from `BaseEnv`:

```python
from bakelib.environ import BaseEnv, EnvBakebook


class MyEnv(BaseEnv):
    ENV_ORDER = ["dev", "sit", "qa", "uat", "prod"]


class MyEnvBakebook(EnvBakebook[MyEnv]):
    env: MyEnv = MyEnv("local")
```

For more details, see the [bakelib source](https://github.com/wislertt/bakefile/tree/main/src/bakelib).

## Development

### Environment Setup

Clone and install the project:

```bash
git clone https://github.com/wislertt/bakefile.git
cd bakefile

# Install bakefile as a global tool
uv tool install bakefile

# Setup development environment (macOS only)
# Installs brew, bun, uv, and pre-commit hooks
bake setup-dev

# Verify development environment is setup correctly
# Checks tool locations and runs lint + test
bake assert-setup-dev
```

**Note:** `bake setup-dev` only supports macOS. For other platforms, run `bake --dry-run setup-dev` to see the commands and follow platform-specific alternatives.

The project uses [uv](https://github.com/astral-sh/uv) for dependency management.

### Testing

Run tests using the bake commands:

```bash
bake test              # Unit tests (fast)
bake test-integration  # Integration tests (slow, real subprocess)
bake test-all          # All tests with coverage
```

### Code Quality

Run linters and formatters before committing:

```bash
bake lint              # Run prettier, toml-sort, ruff format, ruff check, ty, deptry
```

**Verification workflow:**

1. Make changes
2. Run `bake lint` to check code quality
3. Run `bake test` to verify unit tests pass
4. Commit when both pass

## Contributing

Contributions are welcome! Please see [CLAUDE.md](/.claude/CLAUDE.md) for development guidelines, including:

- Project structure and testing conventions
- Code quality standards
- Development workflow

## License

Licensed under the Apache License 2.0. See [LICENSE](/LICENSE) for the full text.
