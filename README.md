[![tests](https://img.shields.io/github/actions/workflow/status/wislertt/bakefile/cd.yml?branch=main&label=tests&logo=github)](https://github.com/wislertt/bakefile/actions/workflows/cd.yml)
[![release](https://img.shields.io/github/actions/workflow/status/wislertt/bakefile/cd.yml?branch=main&label=release&logo=github)](https://github.com/wislertt/bakefile/actions/workflows/cd.yml)
[![quality-gate-status](https://sonarcloud.io/api/project_badges/measure?project=wislertt_bakefile&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=wislertt_bakefile)
[![security-rating](https://sonarcloud.io/api/project_badges/measure?project=wislertt_bakefile&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=wislertt_bakefile)
[![vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=wislertt_bakefile&metric=vulnerabilities)](https://sonarcloud.io/summary/new_code?id=wislertt_bakefile)
[![codecov](https://codecov.io/gh/wislertt/bakefile/graph/badge.svg?token=G0ZRDBGAJB)](https://codecov.io/gh/wislertt/bakefile)
[![ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json&color=green)](https://github.com/astral-sh/ruff)
[![ty](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ty/main/assets/badge/v0.json&color=green)](https://github.com/astral-sh/ty)
[![pypi](https://img.shields.io/pypi/v/bakefile.svg?color=blue)](https://pypi.python.org/pypi/bakefile)
[![status](https://img.shields.io/pypi/status/bakefile)](https://pypi.python.org/pypi/bakefile)
[![license](https://img.shields.io/pypi/l/bakefile)](https://pypi.python.org/pypi/bakefile)
[![downloads](https://static.pepy.tech/personalized-badge/bakefile?period=total&units=international_system&left_color=grey&right_color=blue&left_text=pypi%20downloads)](https://pepy.tech/projects/bakefile)
[![python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue?logo=python)](https://github.com/wislertt/bakefile/)

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://cdn.jsdelivr.net/gh/wislertt/bakefile@main/docs/img/brand/bakefile-lockup-dark.svg">
    <img src="https://cdn.jsdelivr.net/gh/wislertt/bakefile@main/docs/img/brand/bakefile-lockup.svg" width="360" alt="bakefile logo">
  </picture>
</p>

# bakefile

An OOP task runner. Write tasks once, reuse everywhere. Like a Makefile, but reusable and in Python.

## Why bakefile?

- **Reusable** - Makefile and Justfile work well, but reusing tasks across projects is hard. bakefile makes tasks Python class methods, so you inherit and share them like any other code.
- **Python** - Write Python instead of a DSL. Real language features, type checking with ruff and ty, and the rest of Python's tooling. `ctx.run()` still handles normal CLI commands through subprocess.
- **Language-agnostic** - Tasks are Python, but the commands they run can target any language (Go, Rust, JS, etc.).

### How it compares

bakefile vs the runners you probably already know:

|                                 | **bakefile**                                           | Make               | Just                   | Task              | mise                  | Invoke                                 |
| ------------------------------- | ------------------------------------------------------ | ------------------ | ---------------------- | ----------------- | --------------------- | -------------------------------------- |
| Tasks are                       | Python class methods (shell via `ctx.run()`)           | shell recipes      | shell recipes          | shell recipes     | shell recipes         | Python functions (shell via `c.run()`) |
| Type-safe task args             | ✅ Typer                                               | ❌ positional `$@` | ❌ recipe params (str) | ❌ CLI vars (str) | ❌ env vars (str)     | ❌ named, unvalidated                  |
| Auto help + completion\*        | ✅ Typer                                               | ❌                 | ⚠️                     | ⚠️                | ⚠️                    | ⚠️                                     |
| Task reusability                | ✅ inherit + override + compose                        | ⚠️ include         | ⚠️ modules             | ⚠️ includes       | ⚠️ templates (extend) | ⚠️ import                              |
| Prebuilt task libraries         | ✅ [bakelib Spaces](#spaces)                           | ❌                 | ❌                     | ❌                | ❌                    | ✅ invocations                         |
| Language                        | Python                                                 | Make DSL           | Just DSL               | YAML              | TOML                  | Python                                 |
| Type-check / lint / format      | ✅ ruff + ty (native), any Python tool                 | ❌                 | ⚠️ `just --fmt`        | ❌                | ❌                    | ✅ any Python tool                     |
| Logging & console               | ✅ [Rich + loguru](#logging-and-console-output)        | ❌                 | ❌                     | ❌                | ⚠️ log levels         | ⚠️ bring your own                      |
| Typed & validated config\*\*    | ✅ Pydantic BaseSettings                               | ❌ shell vars      | ❌ shell vars          | ❌ templated vars | ❌ env vars           | ❌ Python dict                         |
| Secrets management              | ✅ [SecretUtils](#secrets)                             | ❌                 | ❌                     | ❌                | ❌                    | ❌                                     |
| Multi-environment management    | ✅ [EnvBakebook](#multi-environment-bakebooks) (typed) | ❌                 | ❌                     | ❌                | ✅ MISE_ENV files     | ❌                                     |
| Single binary, no runtime\*\*\* | ❌ needs Python                                        | ✅                 | ✅                     | ✅                | ✅                    | ❌ needs Python                        |
| Inline deps (PEP 723)\*\*\*\*   | ✅                                                     | N/A                | N/A                    | N/A               | N/A                   | ❌                                     |
| Manages tool versions           | ⚠️ bakelib uses mise                                   | ❌                 | ❌                     | ❌                | ✅                    | ❌                                     |

Legend: ✅ yes · ⚠️ partial · ❌ no · N/A not applicable.

\* _Auto help + completion_: ⚠️ tools list and complete task names. bakefile's Typer renders full per-task `--help` (typed options) and completes flags too (`bake --install-completion`).

\*\* _Typed & validated config_: typed Pydantic settings ([Pydantic Settings](#pydantic-settings)) that export to shell, dotenv, JSON, or YAML, or inject into a subprocess's environment ([`env`](#env), [`export`](#export)).

\*\*\* _Single binary, no runtime_: bakefile needs a Python runtime, eased by PEP 723 and `uv`.

\*\*\*\* _Inline deps (PEP 723)_: bakefile's `bakefile.py` can declare its own dependencies inline (`# /// script`), so a single file carries its own dependencies, no project setup needed. PEP 723 is a Python-only standard, so non-Python runners are N/A. bakefile also works with `pyproject.toml` for normal Python projects. PEP 723 is optional. Invoke has no inline-deps mechanism.

Most runners are DSLs over shell recipes. Invoke is Python too, but its tasks are flat module functions with no inheritance or composition model. bakefile is the only one where tasks are class methods you inherit, override, and compose, so reusable task libraries ([bakelib Spaces](#spaces)) just work.

bakefile is new, built on modern typed Python (Typer + Pydantic). **Production-proven:** I run it daily at my company.

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

Or generate one automatically:

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
- **`bakefile`** - Manages your `bakefile.py` (init, add-inline, lint, sync, lock, add, pip, venv, find-python, which, run, env, export)

Detailed CLI documentation in [Usage](#usage).

### Bakebook

A class in `bakefile.py` that holds your tasks:

- Subclass it to share tasks across projects through normal inheritance.
- It extends Pydantic's `BaseSettings`, so configuration is typed class attributes with validation, env-var and `.env` loading, defaults, and type coercion.
- Tasks use the `@command()` decorator, same syntax as Typer.
- `ctx.run()` executes CLI commands through Python's subprocess.

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

bakefile supports [PEP 723](https://peps.python.org/pep-0723/) inline script metadata, so your `bakefile.py` can declare its own dependencies. Add it to an existing bakefile with `bakefile add-inline`:

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

This suits non-Python projects without a `pyproject.toml`. For Python projects, add bakefile to your project's dependencies instead.

## Usage

### Bakebook API

#### Creating a Bakebook

You can also generate one with `bakefile init` or `bakefile add-inline`.

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

#### Logging and Console Output

bakefile has two output channels, and they don't affect each other:

- **`console`** is your task's user-facing output (results, status). It always prints, regardless of verbosity.
- **Logs** are bakefile's own diagnostics, plus any `logging` calls you make in tasks. These are gated by verbosity.

##### Console output

`console` (imported from `bake`) is a thin wrapper over [Rich](https://rich.readthedocs.io/). Print task output through it rather than `print`:

```python
from bake import Bakebook, command, console


class MyBakebook(Bakebook):
    @command()
    def status(self) -> None:
        console.echo("Building...")  # plain output, stdout
        console.success("Build done")  # ✅ SUCCESS   (stderr)
        console.warning("Low disk")  # ⚠️ WARNING   (stderr)
        console.error("Build failed")  # ❌ ERROR     (stderr)
```

Helpers:

- `console.echo(msg)` prints to stdout (your task's normal output).
- `console.success`, `info`, `warning`, `error(msg)` print a labeled line to stderr. In GitHub Actions, `warning` and `error` become `::warning::` / `::error::` annotations.
- `console.prefix(msg, label=..., emoji_code=..., label_style=...)` prints a custom labeled line when the built-in labels don't fit. `label` is required — use `info` for the default `INFO` label.
- `console.cmd(cmd_str)` prints a command as `❯ <cmd>`, which is what `ctx.run` uses to show the command it runs. The arrow accepts `arrow_style=` (default green, e.g. `arrow_style="bold red"` for failed commands); the command text always stays plain.
- `console.script_block(title, script)` pretty-prints a multi-line script, used by `run_script`.

Every helper accepts rich print kwargs (`style`, `emoji`, `markup`, `highlight`, ...) and they apply to the message only — the label chrome is rendered as a `Text` object and is never affected. Chrome styling has its own param names (`label_style` on `prefix`, `arrow_style` on `cmd`) so rich kwargs are never shadowed. So `console.success("tests[unit] passed", markup=False)` keeps the green label but prints the message literally. Note that with markup on (the default), rich parses the message: `[unit]`-style tags are consumed.

Stream model: `echo` is for machine-readable data (stdout, safe to pipe); everything else is human progress output (stderr). Any helper also accepts `no_color=True` to emit zero ANSI codes — use it when the output is parsed by another tool:

```python
console.echo(value, no_color=True)  # clean stdout, no ANSI codes
```

For anything else, the raw Rich consoles are also exposed: `console.out` / `console.err` (stdout / stderr, color) and `console.plain_out` / `console.plain_err` (no color).

`console` output, plain `print()`, and command output are all separate from logs. They always print, regardless of verbosity.

##### Logging

bakefile logs through [loguru](https://github.com/Delgan/loguru), and all logs go to stderr. Standard-library `logging` is bridged into it, so any `logging.getLogger(__name__).info(...)` in your tasks honors the same settings:

```python
import logging

logger = logging.getLogger(__name__)


@bakebook.command()
def task(self):
    logger.info("starting")  # visible at -vv and above
```

Three settings control logs. The first two decide what shows, and the third picks the format.

**Verbosity** sets the global floor. Anything below it is dropped. The default is `0` (silent).

| Flag   | Env                    | Level            |
| ------ | ---------------------- | ---------------- |
| (none) | `BAKE_LOG_VERBOSITY=0` | silent (no logs) |
| `-v`   | `BAKE_LOG_VERBOSITY=1` | warning          |
| `-vv`  | `BAKE_LOG_VERBOSITY=2` | info             |
| `-vvv` | `BAKE_LOG_VERBOSITY=3` | debug            |

```bash
bake build              # silent
bake -v build           # warning + error
bake -vv build          # adds info
bake -vvv build         # adds debug (everything)
```

**Per-module levels** (`--bake-log`, env `BAKE_LOG`) is a comma-separated list of `level` or `module=level` entries. It raises or lowers specific modules independent of verbosity. The default is `warning,bake=debug,bakelib=debug,bakefile=debug` (the tool's internals and your `bakefile.py` at debug, everything else at warning):

```bash
# Set one level for everything (the root level, always required)
bake --bake-log debug build                        # all modules at debug
bake --bake-log warning build                      # all modules at warning

# Raise one module above the root
bake --bake-log warning,bake=debug build           # bake internals at debug, rest warning

# Target your own bakefile.py (it loads as module "bakefile")
bake --bake-log warning,bakefile=debug build       # your bakefile.py at debug

# Env var form: quiet bakefile.py, keep bake internals (restate them)
BAKE_LOG="warning,bake=debug,bakelib=debug,bakefile=warning" bake build
```

`--bake-log` replaces the default instead of merging with it, so restate any module you want to keep. In the last line, `bake` and `bakelib` stay at debug while `bakefile.py` is silenced to warning.

A log line shows only if it clears **both** the verbosity floor and its module's level. So with the default `BAKE_LOG`, `-v` surfaces bakefile's warnings and errors, and `-vvv` surfaces its debug logs too.

**Format** (`--log-pretty` / `--no-log-pretty`, env `BAKE_LOG_PRETTY`, default pretty) chooses between pretty colored text and JSON (one object per line, for CI and log shipping):

```bash
bake --no-log-pretty build     # JSON logs
```

For advanced needs, override `setup_logging()` (e.g. a custom JSON sink like `GCPJsonSink` for GCP Cloud Logging) or `get_bake_log_thread_local_context()` (inject trace IDs into each log line) on your Bakebook.

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

#### Logging Flags

`-v` / `-vv` / `-vvv` (env `BAKE_LOG_VERBOSITY` 0-3) control bakefile's internal logs, plus per-module levels with `--bake-log` (env `BAKE_LOG`) and format with `--log-pretty` (env `BAKE_LOG_PRETTY`). See [Logging and Console Output](#logging-and-console-output) for the full reference. This only affects logs, not `console.echo`, `print`, or command output.

#### Chaining Commands

Run multiple commands sequentially:

```bash
bake -c lint test build
```

If any command fails, the chain stops.

#### Options

Override defaults when running bake:

```bash
bake --version                           # Show version
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
bakefile init -i        # With PEP 723 inline metadata (--inline)
bakefile init --force   # Force overwrite existing bakefile
```

#### add-inline

Add PEP 723 inline metadata to an existing bakefile:

```bash
bakefile add-inline
```

#### lint

Lint `bakefile.py` (or the entire project) with ruff format, ruff check, and ty. Disable any with `--no-ruff-format`, `--no-ruff-check`, or `--no-ty`:

```bash
bakefile lint                   # Lint bakefile.py and all Python files
bakefile lint -b                # Lint only bakefile.py (--only-bakefile)
bakefile lint --no-ty           # Skip type checking
bakefile lint --line-length 88  # Override ruff line length (default 100)
```

#### uv-based commands (PEP 723 bakefile.py only)

Convenience wrappers around `uv` commands with `--script bakefile.py` added. For PEP 723 bakefile.py files only. For normal Python projects, use your preferred dependency manager (pip, poetry, uv, etc.).

```bash
bakefile sync                   # = uv sync --script bakefile.py
bakefile sync --upgrade         # -U; upgrade package dependencies
bakefile sync --reinstall       # Reinstall all packages
bakefile lock                   # = uv lock --script bakefile.py
bakefile lock --upgrade         # -U; upgrade locked dependencies
bakefile add requests           # = uv add --script bakefile.py requests
bakefile pip install            # = uv pip install --python <bakefile-python-path>
```

Extra args pass through to `uv` (e.g. `bakefile sync --frozen`, `bakefile lock --no-build`).

#### venv

Ensure a `.venv` exists in the repo root. For PEP 723 standalone bakefiles, symlinks `.venv` to the uv-managed environment. For standard Python projects (`pyproject.toml`), it just runs `uv sync`, so prefer `uv` directly there:

```bash
bakefile venv            # Create or update .venv (standalone bakefiles)
bakefile venv --force    # Replace an existing .venv symlink (standalone only)
```

#### find-python

Print the Python path used by `bake`, `bakefile env`, `bakefile export`, `bakefile run`, and `bakefile lint` (the bakefile's Python):

```bash
bakefile find-python
```

#### which

Diagnose which Python each command uses. `bake`, `bakefile env`, and `bakefile export` reinvoke under the bakefile's Python (they re-run themselves and load the bakebook). `bakefile run` and `bakefile lint` spawn that Python directly to run your code (no self-reinvoke, no bakebook). All other subcommands use the invoked Python:

```bash
bakefile which
```

#### run

Run a script or module under the bakefile's Python (like `uv run` for the bakefile's environment). If the first argument is an existing file, it runs as `python script.py`. Otherwise it runs as `python -m module`:

```bash
bakefile run test.py            # Run a script (python test.py)
bakefile run pytest tests/      # Run as a module (python -m pytest tests/)
bakefile run ruff check src/    # Module with arguments
```

#### env

Print or inject bakebook variables. Given this `bakefile.py`:

```python
from bake import Bakebook
from pydantic import SecretStr


class MyBakebook(Bakebook):
    database_url: str = "postgres://localhost/myapp"
    api_key: SecretStr = SecretStr("hunter2")


bakebook = MyBakebook()
```

Print a value (output is shell-quoted):

```bash
bakefile env DATABASE_URL        # postgres://localhost/myapp
bakefile env API_KEY             # '**********'  (SecretStr masked)
bakefile env API_KEY -s          # hunter2       (--secret reveals it)
```

Inject variables into a command's environment with `--` (`printenv` reads the injected value):

```bash
# Inject all variables (none named before --)
bakefile env -- printenv DATABASE_URL            # postgres://localhost/myapp

# Inject only API_KEY, with -s to reveal the secret
bakefile env -s API_KEY -- printenv API_KEY      # hunter2
```

#### export

Export bakebook variables to shell, dotenv, JSON, or YAML. By default it exports every field, including bake's internal settings, so use `-i` to focus on your own. Using the same `bakefile.py` as `env` above:

```bash
# Default: all fields
bakefile export
# export BAKE_LOG=warning,bake=debug,bakelib=debug,bakefile=debug
# export BAKE_LOG_VERBOSITY=0
# export BAKE_LOG_PRETTY=true
# export DATABASE_URL=postgres://localhost/myapp
# export API_KEY='**********'

# Filter to specific fields with -i
bakefile export -i database_url -i api_key
# export DATABASE_URL=postgres://localhost/myapp
# export API_KEY='**********'

bakefile export -f json -i database_url -i api_key
# {
#   "database_url": "postgres://localhost/myapp",
#   "api_key": "**********"
# }
```

Formats: `sh` (default), `dotenv`, `json`, `yaml`. Secrets stay masked unless you pass `-s`. Write to a file with `-o`:

```bash
bakefile export -f dotenv -o .env          # .env file
bakefile export -f json -o config.json     # JSON file
bakefile export -f yaml -o config.yaml     # YAML file
```

### `bakelib` - Optional Helpers

**bakelib** is an optional collection of opinionated helpers built on top of Bakebook. Includes Spaces (pre-configured tasks) and Environ (multi-environment support).

Install with:

```bash
pip install bakefile[lib]
```

bakelib is optional; bakefile works without it. You can also write your own Bakebook classes if you prefer different conventions.

#### Spaces

A **Space** is a Bakebook preconfigured for a project type. They share a common base and compose through inheritance: `BaseSpace` holds the shared tasks (lint, clean, setup-dev, tools, update, version), then `PythonSpace` and `RustSpace` add language-specific lint, test, and tool setup, and `PythonLibSpace` and `RustLibSpace` add publishing on top. `GitHubActionsTools`, `BaseServiceSpace`, and `SubmodulesUtils` extend `BaseSpace` directly.

The prebuilt spaces:

- `PythonSpace` - Python lint, test, and dev setup (ruff, ty, deptry, pytest)
- `RustSpace` - Rust lint, tool setup, and update (clippy, fmt, rustup, cargo)
- `PythonLibSpace` - `PythonSpace` plus `publish` (PyPI / TestPyPI)
- `RustLibSpace` - `RustSpace` plus `publish` (crates.io)
- `GitHubActionsTools` - GitHub Actions linting (actionlint) and updates
- `BaseServiceSpace` - build / deploy / destroy hooks to override
- `SubmodulesUtils` - sync git submodules

`PythonSpace` below is the worked example.

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
- ...and more (run `bake --help`)

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
- ...and more

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
class DevBakebook(DevEnvMixin, EnvBakebook[BaseEnv]): ...


class StagingBakebook(StagingEnvMixin, EnvBakebook[BaseEnv]): ...


class ProdBakebook(ProdEnvMixin, EnvBakebook[BaseEnv]): ...


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
    ENV_PRIORITY_ORDER = ("dev", "sit", "qa", "uat", "prod")


class MyEnvBakebook(EnvBakebook[MyEnv]):
    env: MyEnv = MyEnv("dev")
```

#### Refreshable Cache

`RefreshableCacheRegistry` is a standalone refreshable cache for secrets or any fetched values, usable in any Python project with no Bakebook required. Subclass `FetchFn` to declare how a value is fetched, register it under a key, and the first `get` fetches and caches it.

```python
from dataclasses import dataclass

from bakelib.refreshable_cache import FetchFn, KeyringCache, MemoryCache, RefreshableCacheRegistry


@dataclass(frozen=True)
class GcpSecretFetchFn(FetchFn[str]):
    project_id: str
    secret_id: str

    def __call__(self) -> str:
        # Real implementation calls the GCP Secret Manager API here
        return "dummy-secret-value"


registry = RefreshableCacheRegistry[str](namespace="myapp", backends=[MemoryCache, KeyringCache])
registry.insert_cache(
    "api_key",
    fetch_fn=GcpSecretFetchFn(key="api_key", project_id="my-project", secret_id="api-key"),
)

registry.get("api_key")  # fetches and caches on first call
registry.refresh("api_key")  # force a re-fetch
registry.has_value("api_key")  # True once cached
```

For secrets rotated while your process runs, wrap the call in `@cache.catch_refresh` and raise `RefreshNeededError` when the service rejects the cached value:

```python
cache = registry.get_cache("api_key")


@cache.catch_refresh
def call_api() -> str:
    token = cache.get()
    response = api_request(token)  # your code
    if response.status == 401:  # token rejected (rotated server-side)
        raise cache.RefreshNeededError
    return response.body
```

The cache then clears and `call_api` retries, re-fetching a fresh token via `cache.get()`. Retries are tenacity-backed (`stop`/`wait`, defaults 2 attempts, no delay), so secrets refresh at runtime with no restart. `acatch_refresh` is the async variant.

Backends: `MemoryCache` (default, ephemeral), `KeyringCache` (system keyring, persistent), `ChainedCache` (several, read-first/write-all), `NullCache` (disabled). A single backend is used directly, multiple are wrapped in `ChainedCache`. Pass `ttl=` for expiry.

#### Secrets

`SecretUtils` is a `Bakebook` mixin from `bakelib.utils` that wires a `RefreshableCacheRegistry` into your bakebook and adds the `bake secret` commands. It reuses the same `FetchFn` you defined above. Override `get_secret_fetch_fns` to declare which keys are tracked:

```python
from bakelib.utils import SecretUtils


class MyBakebook(SecretUtils[str]):
    def get_secret_fetch_fns(self):
        return (GcpSecretFetchFn(key="api_key", project_id="my-project", secret_id="api-key"),)
```

Only tracked keys can be set or read. The `bake secret` group:

- `bake secret list` - tracked keys with cached/not-cached status (shows the namespace)
- `bake secret get KEY` - print a cached value
- `bake secret set KEY VALUE` - store a value (plain, not prompted)
- `bake secret del [KEY]` - delete one key, or all if none given
- `bake secret refresh [KEY]` - re-run the fetch functions for one key, or all

The default backend chain is `MemoryCache` + `KeyringCache` under the namespace `"bakebook"`. Override `get_secret_namespace()` to isolate secrets per project.

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

Contributions are welcome. See [CLAUDE.md](/.claude/CLAUDE.md) for development guidelines, including:

- Project structure and testing conventions
- Code quality standards
- Development workflow

## License

Licensed under the Apache License 2.0. See [LICENSE](/LICENSE) for the full text.

The wordmark in `docs/img/brand/` uses outlined paths from [Shantell Sans](https://fonts.google.com/specimen/Shantell+Sans), licensed under the [SIL Open Font License 1.1](https://openfontlicense.org/open-font-license-official-text/).
