# PROJECT_KNOWLEDGE.md

**Architecture overview and integration points for bakefile**

## Project Overview

**bakefile** is a Python-based task runner (Make/Justfile alternative) that uses OOP for task/recipe reusability.

**Key design goal:** Unlike Makefiles where tasks are not reusable, bakebook uses OOP patterns allowing tasks and variables to be composed, inherited, and reused.

## Core Concepts

| Term            | Purpose                                                            |
| --------------- | ------------------------------------------------------------------ |
| **bakefile.py** | User's task definition file (like Makefile, but Python)            |
| **bakebook**    | OOP container holding commands + variables (reusable, composable)  |
| **bake**        | CLI that loads bakefile.py and executes bakebook commands          |
| **bakefile**    | Management CLI for bakefile projects (init, lint, sync, lock, add) |

## Architecture

```
┌─────────────────────────────────────────────┐
│           User's Repository                 │
│  bakefile.py  (like Makefile, but Python)   │
│                                             │
│  from bake import Bakebook                  │
│  bakebook = Bakebook()                      │
│                                             │
│  @bakebook.command()                        │
│  def build():                               │
│      ...                                    │
└─────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│              bake CLI                       │
│  1. get_bakefile_object() -> BakefileObject │
│  2. bakebook_obj.get_bakebook()             │
│  3. Execute commands via typer app          │
└─────────────────────────────────────────────┘
```

## Bakebook Evolution

The `bakebook` object has evolved through phases:

| Phase        | bakebook Type    | Description                                |
| ------------ | ---------------- | ------------------------------------------ |
| v1 (past)    | `typer.Typer`    | Commands only - enables subcommand support |
| v2 (current) | `Bakebook` class | Full OOP: commands + env validation        |

## Component Interactions

```
User runs: bake -C /path/to/project build --prod

bake CLI:
  1. get_bakefile_object() -> BakefileObject
     - Parses CLI args (-C, --file-name, --book-name, --dry-run)

  2. bakefile_obj.get_bakebook()
     - resolve_bakefile_path(path, file_name)
       - get_target_dir_path() if -C specified
       - validate_file_name()
     - load_module(path) - import bakefile.py
     - get_bakebook_from_target_dir_path(path, bakebook_name)
       - get_bakebook_from_module()
       - validate_bakebook() - ensure Bakebook instance

  3. Execute bakebook(args=["build", "--prod"])
     - Bakebook's internal Typer runs the build command
```

### Context Re-Export

**As of 2025-01-04:** `Context` is re-exported from `bake/__init__.py` for easier importing.

**User API:**

```python
# Class-based command (recommended)
class MyBakebook(Bakebook):
    @command()
    def build(self) -> None:
        # Access dry_run flag via self.ctx
        if self.ctx.dry_run:
            console.echo("[DRY RUN] Would build")
            return
        # Actual build
        self.ctx.run("cargo build")

bakebook = MyBakebook()

# Standalone function (also works)
from bake import Bakebook, command

bakebook = Bakebook()

@bakebook.command()
def build() -> None:
    # Access dry_run flag via bakebook.ctx
    if bakebook.ctx.dry_run:
        console.echo("[DRY RUN] Would build")
        return
    # Actual build
    bakebook.ctx.run("cargo build")
```

**Architecture:**

- `src/bake/__init__.py` re-exports `Context` from `bake.cli.common.context`
- `Context` is a subclass of `typer.Context` with typed `obj: BakefileObject`
- `Bakebook.ctx` property provides direct access to the CLI context
- In class-based commands, use `self.ctx`; in standalone commands, use `bakebook.ctx`

**Important Notes:**

- The `ctx` parameter is no longer needed in command signatures - use `self.ctx` or `bakebook.ctx`
- In `bake/cli/common/params.py` and `bake/cli/common/obj.py`, `typer.Context` is used (not `Context`) to avoid circular imports
- In user-facing CLI commands (`bake/cli/bakefile/*.py`), use `Context` from `bake` for callbacks
- In tests, import `Context` from `bake` for consistency

## Data Flow

```
bake command → get_bakefile_object() → BakefileObject
                │
                └── bakebook_obj.get_bakebook()
                    ├── resolve_bakefile_path()
                    ├── load_module()
                    ├── get_bakebook_from_target_dir_path()
                    └── validate_bakebook()
                    │
                    ▼
                    typer.Typer → user's task execution
```

## Technology Stack Decisions

| Technology   | Purpose                                              |
| ------------ | ---------------------------------------------------- |
| **Typer**    | CLI framework (used by both bake and user bakebooks) |
| **Click**    | Lower-level CLI framework (used by Typer internally) |
| **Rich**     | Terminal output formatting with colors and emojis    |
| **Loguru**   | Zero-boilerplate logging with verbosity support      |
| **orjson**   | Fast JSON serialization for logging (10x faster)     |
| **Pydantic** | Validation and settings (future: bakebook variables) |
| **UV**       | Fast Python package management                       |
| **pytest**   | Testing                                              |
| **ty**       | Linting                                              |

## File Organization

```
src/
├── bake/                # Main package (import name: "bake")
│   ├── __init__.py          # Package initialization, version handling
│   ├── bakebook/            # Core bakebook functionality
│   │   ├── __init__.py
│   │   ├── bakebook.py      # Bakebook class (BaseSettings + Typer)
│   │   └── get.py           # File/module loading, bakebook resolution
│   ├── manage/              # Bakefile management logic (PEP 723, Python detection)
│   │   ├── __init__.py
│   │   ├── add_inline.py    # PEP 723 inline metadata functions
│   │   └── find_python.py   # Python discovery (two-level: bakefile-level vs project-level)
│   ├── cli/                 # CLI components
│   │   ├── __init__.py
│   │   ├── common/          # Shared code between bake and bakefile CLIs
│   │   │   ├── __init__.py
│   │   │   ├── app.py               # BakefileApp base class, show_help_if_no_command
│   │   │   ├── callback.py          # Validation callbacks for typer options
│   │   │   ├── context.py           # Context subclass with BakefileObject obj type
│   │   │   ├── exception_handler.py # Custom Typer exception handling
│   │   │   ├── obj.py               # BakefileObject dataclass, get_bakefile_object()
│   │   │   └── params.py            # Shared typer options (chdir, file-name, book-name, version)
│   │   ├── bake/            # bake CLI (runs user tasks)
│   │   │   ├── __init__.py
│   │   │   └── main.py              # Entry point
│   │   ├── bakefile/        # bakefile management CLI
│   │   │   ├── __init__.py
│   │   │   ├── add_inline.py        # Add inline metadata command
│   │   │   ├── find_python.py       # Find Python command
│   │   │   ├── init.py              # Init command
│   │   │   ├── lint.py              # Lint command (ruff, ty)
│   │   │   ├── main.py              # Entry point
│   │   │   └── uv.py                # UV commands (pip, add, lock, sync)
│   │   └── utils/            # CLI utilities
│   │       ├── __init__.py
│   │       └── version.py          # Version callback
│   ├── samples/             # Sample bakebook implementations
│   │   ├── __init__.py
│   │   └── simple.py              # Simple sample bakebook
│   ├── ui/                  # User-facing output tools
│   │   ├── __init__.py
│   │   ├── console.py            # Rich-based console output (success, info, warning, error)
│   │   ├── run/                  # Command execution utilities
│   │   │   ├── __init__.py       # Exports: run, run_script, run_uv, OutputSplitter
│   │   │   ├── run.py            # run() - execute single commands
│   │   │   ├── script.py         # run_script() - execute multi-line scripts
│   │   │   ├── splitter.py       # OutputSplitter class for PTY/stream handling
│   │   │   └── uv.py             # run_uv() - execute uv commands
│   │   └── logger/              # Loguru-based logging utilities
│   │       ├── __init__.py       # Exports logger, setup_logging, capsys helpers
│   │       ├── capsys.py         # Test helpers: capsys_to_logs, parse_pretty_log
│   │       ├── setup.py          # setup_logging() function
│   │       └── utils.py          # InterceptHandler, PrettyLogFormatter, JsonSink
│   └── utils/               # Package-level utilities
│       ├── __init__.py
│       ├── constants.py           # DEFAULT_FILE_NAME, DEFAULT_BAKEBOOK_NAME, GET_BAKEFILE_OBJECT
│       ├── env.py                 # NO_COLOR support (should_use_colors)
│       └── exceptions.py          # BakebookError, BaseBakefileError
└── bakelib/             # Optional extra library (install: `pip install bakefile[lib]`)
    ├── __init__.py
    └── hello.py              # PoC module with extra dependencies (e.g., requests)

tests/
├── bake/                # Tests for bake package
│   ├── bakebook/
│   ├── cli/
│   ├── manage/
│   ├── ui/
│   └── test_init.py
├── bakelib/             # Tests for bakelib package
│   └── test_hello.py
├── conftest.py          # Shared fixtures (disable colors)
└── conftest_utils/      # Test utility modules
```

**Note:** The import package is named `bake` (not `bakefile`) to avoid conflicts with user's `bakefile.py` files. Install remains as `pip install bakefile`.

## Shared CLI Architecture

Both `bake` and `bakefile` CLIs (from bake package) share common code in `src/bake/cli/common/`:

| Module                 | Purpose                                                                                                                                             |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `app.py`               | `BakefileApp` base class (extends `typer.Typer`), `rich_markup_mode`, `add_completion`, `show_help_if_no_command()`, `bake_app_callback_with_obj()` |
| `callback.py`          | Validation callbacks for typer options (e.g., `validate_file_name_callback`)                                                                        |
| `context.py`           | `Context` subclass (extends `typer.Context`) with typed `obj: BakefileObject`                                                                       |
| `exception_handler.py` | Custom Typer exception handling with rich error formatting                                                                                          |
| `obj.py`               | `BakefileObject` dataclass, `get_bakefile_object()` function for retrieving bakebook from CLI args                                                  |
| `params.py`            | Shared typer option definitions using `Annotated` types (`ChdirOption`, `FileNameOption`, `VerbosityOption`, etc.)                                  |

### Bakebook Module

Core bakebook functionality is in `src/bake/bakebook/`:

| Module / Function                     | Purpose                                             |
| ------------------------------------- | --------------------------------------------------- |
| `bakebook.py`                         | `Bakebook` class (extends BaseSettings with Typer)  |
| `get.py`                              | All bakebook loading and validation logic           |
| `get_target_dir_path()`               | Resolve and optionally create target directory      |
| `resolve_bakefile_path()`             | Resolve full path to bakefile.py                    |
| `load_module()`                       | Import bakefile.py as Python module using importlib |
| `get_bakebook_from_module()`          | Extract bakebook from loaded module                 |
| `get_bakebook_from_target_dir_path()` | Load module and extract bakebook                    |
| `validate_bakebook()`                 | Ensure bakebook is a valid Bakebook instance        |

### Manage Module

Bakefile management functionality is in `src/bake/manage/`:

| Module / Function          | Purpose                                                             |
| -------------------------- | ------------------------------------------------------------------- |
| `add_inline.py`            | PEP 723 inline metadata functions                                   |
| `add_inline_metadata()`    | Add PEP 723 metadata to existing bakefile using uv                  |
| `read_inline()`            | Parse PEP 723 `# /// script` blocks (reference impl)                |
| `find_python.py`           | Python discovery for bakefiles                                      |
| `find_python()`            | Main entry point - two-level detection strategy                     |
| `find_python_path()`       | Get Path to Python interpreter for bakefile                         |
| `is_standalone_bakefile()` | Check if bakefile has PEP 723 metadata (standalone vs project mode) |
| `_find_bakefile_lock()`    | Find `<bakefile.py.lock>`                                           |
| `_find_project_lock()`     | Find `uv.lock` by searching up directory tree                       |
| `_find_bakefile_python()`  | Find existing bakefile-level Python via `uv python find`            |
| `_find_project_python()`   | Find existing project-level Python via `uv python find`             |
| `_create_bakefile_venv()`  | Create bakefile-level venv using `uv sync --script`                 |
| `_create_project_venv()`   | Create project-level venv using `uv sync`                           |
| `lint.py`                  | Linting wrapper functions for ruff and ty                           |
| `run_ruff()`               | Shared function for ruff commands                                   |
| `run_ruff_format()`        | Run ruff format with `only_bakefile` support                        |
| `run_ruff_check()`         | Run ruff check with `only_bakefile` support                         |
| `run_ty_check()`           | Run ty check with `only_bakefile` support                           |
| `run_uv.py`                | UV dependency management command wrappers                           |
| `run_uv_add()`             | Run `uv add --script bakefile.py <args>`                            |
| `run_uv_lock()`            | Run `uv lock --script bakefile.py <args>`                           |
| `run_uv_sync()`            | Run `uv sync --script bakefile.py <args>`                           |
| `run_uv_pip()`             | Run `uv pip <command> <args> --python <path>`                       |

### UV Dependency Management Commands

**Location:** `src/bake/manage/run_uv.py`, `src/bake/cli/bakefile/uv.py`

**Purpose:** Provide bakefile-friendly wrappers around UV package management commands.

**Commands:**

| Command | Scope                 | Injected Args            | Metadata Required |
| ------- | --------------------- | ------------------------ | ----------------- |
| `pip`   | Both inline & project | `--python <path>`        | No                |
| `add`   | Inline metadata only  | `--script <bakefile.py>` | Yes               |
| `lock`  | Inline metadata only  | `--script <bakefile.py>` | Yes               |
| `sync`  | Inline metadata only  | `--script <bakefile.py>` | Yes               |

**Architecture:**

- `run_uv.py` contains all `run_uv_*()` wrapper functions with shared `_run_uv()` helper
- `uv.py` CLI module contains all command handlers (`pip`, `add`, `lock`, `sync`)
- Uses pass-through pattern: no option parsing, just forwards args to uv
- When uv adds new options, they automatically work

**Examples:**

```bash
# Pip - works for both inline and project-level
bakefile pip install requests
bakefile pip list --format=json
bakefile pip freeze

# Add - requires PEP 723 inline metadata
bakefile add requests typer
bakefile add "requests>=2.32.0" --dev

# Lock - requires PEP 723 inline metadata
bakefile lock
bakefile lock --upgrade
bakefile lock --no-build
bakefile lock -U requests typer

# Sync - requires PEP 723 inline metadata
bakefile sync
bakefile sync --upgrade
bakefile sync --reinstall
bakefile sync --frozen
bakefile sync --no-dev
bakefile sync --no-build
```

**Two-Level Detection Strategy:**

| Level              | Trigger                     | Python Scope       | uv Command                            |
| ------------------ | --------------------------- | ------------------ | ------------------------------------- |
| **Bakefile-level** | Has PEP 723 inline metadata | File-isolated venv | `uv python find --script bakefile.py` |
| **Project-level**  | No inline metadata          | Project `.venv`    | `uv python find -v`                   |

**PEP 723 Support:**

- Uses `uv init --script` to initialize inline metadata
- Uses `uv add bakefile --script` to add bakefile as dependency
- Validates that `bakefile` dependency exists in inline metadata
- Supports Python 3.10/3.11+ with conditional `tomli`/`tomllib` import

### Lint Command

**Location:** `src/bake/manage/lint.py`, `src/bake/cli/bakefile/lint.py`

**Purpose:** Quick and strict way to lint bakefile.py and the entire project using ruff and ty.

**Usage:**

```bash
# Lint entire project (all Python files)
bakefile lint

# Lint only bakefile.py
bakefile lint --only-bakefile
bakefile lint -b

# Skip individual linters
bakefile lint --no-ruff-format
bakefile lint --no-ruff-check
bakefile lint --no-ty

# Combine flags
bakefile lint -b --no-ty  # Only ruff on bakefile, skip type check
```

**Default behavior:** Runs ruff format, ruff check, and ty check on all Python files in the project.

**Flags:**

| Flag               | Purpose                                   |
| ------------------ | ----------------------------------------- |
| `--only-bakefile`  | Lint only bakefile.py, not entire project |
| `--no-ruff-format` | Skip ruff format                          |
| `--no-ruff-check`  | Skip ruff check                           |
| `--no-ty`          | Skip ty type checking                     |

**Architecture:**

- `lint.py` (manage module) contains wrapper functions using `find_ruff_bin()` and `find_ty_bin()`
- `lint.py` (cli module) contains the command handler
- Uses fail-fast pattern: stops on first linter failure
- `only_bakefile` pattern: target = `bakefile.name` if True else `.`

### BakefileObject Pattern

Instead of passing CLI args through many function calls, both CLIs use `BakefileObject`:

```python
@dataclass
class BakefileObject:
    chdir: Path
    file_name: str
    bakebook_name: str
    bakefile_path: Path | None = None
    bakebook: Bakebook | None = None
    bake_log_verbosity: int = 0
    dry_run: bool = False
    bake_log: str = DEFAULT_BAKE_LOG
    bake_log_pretty: bool = True

    def __post_init__(self):
        # Validate file name on initialization
        validate_file_name(self.file_name)

    def setup_logging(self):
        # Reset idempotency guard, then configure logging
        # Uses bakebook's bake_log/bake_log_pretty when available
        # Falls back to own bake_log/bake_log_pretty otherwise
        # Verbosity always comes from self.bake_log_verbosity (CLI)

    def get_bakebook(self):
        # Load bakebook if not already loaded
        # Uses contextlib.suppress(BakebookError) for graceful handling

    def warn_if_no_bakebook(self, color_echo: bool):
        # Show warning if bakebook not found
```

Usage:

```python
bakefile_obj = get_bakefile_object()  # Parses CLI args
bakefile_obj.get_bakebook()
bakefile_obj.warn_if_no_bakebook(color_echo=env.should_use_colors())
```

### Dry Run Flag

**As of 2025-01-04:** `--dry-run` / `-n` flag is available on both `bake` and `bakefile` CLIs.

**User API:**

```python
class MyBakebook(Bakebook):
    @command()
    def deploy(self) -> None:
        if self.ctx.dry_run:
            console.echo("[DRY RUN] Would deploy to production")
            return

        # Actual deployment
        console.success("Deploying...")
        self.ctx.run("kubectl apply -f deployment.yaml")
```

**CLI Usage:**

```bash
# Dry run for bake commands
bake -n hello
bake --dry-run build --prod

# Dry run for bakefile commands (planned, not yet implemented)
bakefile -n lint
bakefile --dry-run uv sync
```

**Architecture:**

- `dry_run` stored in `BakefileObject.dry_run` (single source of truth)
- `Context.dry_run` is a `@property` that returns `self.obj.dry_run`
- Flag controls execution behavior, not output (separation from verbosity)
- `-n` follows common CLI convention (make, nix, etc.)

**Status:**

- ✅ Core infrastructure complete (Phase 1)
- ✅ User commands can access `ctx.obj.dry_run`
- ⏳ Framework commands (`init`, `add-inline`, `lint`, `uv sync`, etc.) do not yet respect dry run (deferred to future work)

### Key Implementation Details

#### get_bakefile_object() Function

The `get_bakefile_object()` function in `obj.py` is a key piece of infrastructure:

1. Creates a hidden typer app (`bakefile_obj_app`) with a hidden command (`get_bakefile_object`)
2. Uses typer's context system to parse CLI args without interfering with the main CLI
3. Filters out `--help` and `--version` to prevent conflicts
4. Returns a `BakefileObject` instance with all parsed parameters

#### Exception Handling

Custom exception handler in `exception_handler.py`:

- Wraps Typer's standard exception handling
- Supports rich formatting when available
- Handles `EOFError`, `KeyboardInterrupt`, `OSError` (EPIPE), `ClickException`, `Exit`, and `Abort`
- Can run in standalone mode (exits on error) or non-standalone mode (propagates exceptions)

#### Samples System

Samples in `src/bake/samples/`:

- Use `__bakebook__` as the bakebook variable name (constant: `BAKEBOOK_NAME_IN_SAMPLES`)
- `init.py` reads sample modules and replaces `__bakebook__` with user's desired bakebook name
- Currently has `simple.py` sample with a `hello` command

## Logging and Console Infrastructure

### Overview

The bakefile CLI uses a two-tier output system:

| Tier        | Purpose              | Module            | Output                    |
| ----------- | -------------------- | ----------------- | ------------------------- |
| **Console** | User-facing messages | `bake.ui.console` | stdout/stderr with colors |
| **Logging** | Internal/debug logs  | `bake.ui.logger`  | stderr (Loguru)           |

### Console Module (`bake.ui.console`)

Rich-based console output for user-facing messages:

```python
from bake.ui import console

console.success("Operation completed")  # Green ✓, stdout
console.echo("Processing data")         # Plain, stdout
console.warning("File not found")       # Yellow ⚠, stderr
console.error("Failed to connect")      # Red ✗, stderr

# Rich markup supported
console.error(f"File [bold]{path}[/bold] not found")
console.echo(f"Run [code]bakefile init[/code] to create one")
```

**Key features:**

- Stream separation: success/info → stdout, warning/error → stderr
- Rich markup: `[bold]`, `[code]`, `[color]` tags
- NO_COLOR environment variable support
- Type hints: `success/warning/error` take `str`, `info` takes `Any`

### Logger Module (`bake.ui.logger`)

Loguru-based logging for internal debugging and user bakefile logs:

```python
from bake.ui import setup_logging
import logging

# Setup with verbosity
setup_logging(
    level_per_module={"": logging.WARNING},  # Default level
    is_pretty_log=False,  # JSON format (True for human-readable)
)
```

**Key components:**

| Component            | Purpose                                                   |
| -------------------- | --------------------------------------------------------- |
| `setup_logging()`    | Configure Loguru with level, format, per-module filtering |
| `InterceptHandler`   | Intercept standard `logging` module and route to Loguru   |
| `PrettyLogFormatter` | Human-readable Rich-formatted logs                        |
| `JsonSink`           | Structured JSON logs (uses `orjson` for speed)            |
| `capsys_to_logs`     | Test helper to capture parsed logs from capsys output     |

**Verbosity levels:**

| Flag   | Level    | Usage                        |
| ------ | -------- | ---------------------------- |
| (none) | Silent   | No log output (verbosity=0)  |
| `-v`   | WARNING+ | Warnings and errors only     |
| `-vv`  | INFO+    | Info, warnings, and errors   |
| `-vvv` | DEBUG+   | All messages including debug |

Verbosity acts as a **global floor** — even if `bake_log` configures a module for DEBUG, the floor set by verbosity blocks messages below it.

### User Bakefile Logging

Users can use standard `logging` module in their bakefiles:

```python
# In bakefile.py
import logging

@bakebook.command()
def build():
    logging.info("Starting build...")
    logging.debug("Loading config...")
    # Build logic here
    logging.info("Build complete!")
```

All `logging` calls are intercepted and formatted consistently with the CLI's Loguru setup.

### Unified Logging Configuration

Bakebook has three logging configuration fields that unify CLI and non-CLI logging:

```python
from bake import Bakebook

class MyBakebook(Bakebook):
    bake_log: str = "warning,bake=debug,bakelib=debug"
    bake_log_verbosity: int = 0
    bake_log_pretty: bool = True
```

**Fields:**

| Field                | Type   | Default                                             | Purpose                                 |
| -------------------- | ------ | --------------------------------------------------- | --------------------------------------- |
| `bake_log`           | `str`  | `"warning,bake=debug,bakelib=debug,bakefile=debug"` | Per-module log levels (BAKE_LOG format) |
| `bake_log_verbosity` | `int`  | `0`                                                 | Global minimum log level floor (0-3)    |
| `bake_log_pretty`    | `bool` | `True`                                              | Pretty vs JSON log format               |

**BAKE_LOG format** (RUST_LOG-compatible):

```bash
# Simple global level
bake_log = "info"

# Global + per-module
bake_log = "warning,bake=debug,myapp.database=error"

# Per-module only (no global default)
bake_log = "myapp=debug"
```

**Verbosity as floor:**

- `bake_log` controls what modules **emit** (per-module filter)
- `bake_log_verbosity` controls what logger **outputs** (global floor)
- Floor overrides per-module config

```python
# bake_log="debug", verbosity=1 (WARNING floor)
# → modules emit DEBUG, but logger only outputs WARNING+

# bake_log="debug", verbosity=3 (DEBUG floor)
# → modules emit DEBUG, logger outputs DEBUG+
```

**Two paths to setup_logging:**

1. **CLI path**: `BakefileObject.setup_logging()` — uses bakebook's `bake_log`/`bake_log_pretty` when available, CLI's `bake_log_verbosity` always
2. **Non-CLI path**: `Bakebook.setup_logging()` — uses own `bake_log`, `bake_log_verbosity`, `bake_log_pretty`

**Environment variables:**

```bash
# .env
BAKE_LOG=warning,bake=debug,bakelib=debug
BAKE_LOG_VERBOSITY=1
BAKE_LOG_PRETTY=true
```

## CLI Entry Points

### bake CLI

`src/bake/cli/bake/main.py`:

1. Gets `BakefileObject` from CLI args
2. Loads bakebook if found
3. Creates typer app and adds bakebook as subcommand
4. Runs the app

### bakefile CLI

`src/bake/cli/bakefile/main.py`:

1. Gets `BakefileObject` from CLI args
2. Optionally loads bakebook (doesn't warn if not found)
3. Creates `BakefileApp` and adds commands (e.g., `init`)
4. Runs the app

## Command Execution

### Overview

The `bake.ui.run` module provides subprocess execution utilities with real-time streaming, output capture, color preservation (PTY), and optional echo/dry-run modes.

### Functions

#### `run()` - Execute Commands

**Location:** `src/bake/ui/run/run.py`

Execute single commands with optional display and dry-run:

```python
from bake.ui.run import run

# Show and run (default: echo=True)
run("uv pip install requests")

# Silent execution
run("uv pip install requests", echo=False)

# Preview without running
run("uv pip install requests", dry_run=True)

# Show preview only
run("uv pip install requests", echo=True, dry_run=True)

# Pipes and wildcards (shell=True auto-detected for strings)
run("ls *.py | wc -l")
run("echo hello && echo world")

# List for direct execution (shell=False)
run(["echo", "hello"])

# With timeout (raises subprocess.TimeoutExpired if exceeded)
run("rustup update", timeout=60)
```

**Parameters:**

| Parameter        | Type                  | Default  | Description                                             |
| ---------------- | --------------------- | -------- | ------------------------------------------------------- |
| `cmd`            | `str \| list[str]`    | required | Command as string or list                               |
| `echo`           | `bool`                | `True`   | Display command before execution                        |
| `dry_run`        | `bool`                | `False`  | Skip execution, return success                          |
| `capture_output` | `bool`                | `True`   | Capture stdout/stderr                                   |
| `check`          | `bool`                | `True`   | Raise `typer.Exit` on non-zero                          |
| `cwd`            | `Path \| str \| None` | `None`   | Working directory                                       |
| `stream`         | `bool`                | `True`   | Stream output in real-time                              |
| `shell`          | `bool \| None`        | `None`   | Auto-detect: str→True, list→False                       |
| `timeout`        | `float \| None`       | `None`   | Timeout in seconds (raises `subprocess.TimeoutExpired`) |

**Key behaviors:**

- String commands auto-enable `shell=True` for pipes, wildcards, chaining
- List/tuple commands use `shell=False` for safer direct execution
- On Unix, uses PTY to preserve ANSI color codes
- `echo` and `dry_run` are independent (no auto-coupling)
- `timeout` kills the process tree on expiry (uses `taskkill /F /T` on Windows, `proc.kill()` on Unix)

#### `run_script()` - Execute Shell Scripts

**Location:** `src/bake/ui/run/script.py`

Run multi-line shell scripts with formatted display:

```python
from bake.ui.run import run_script

# Show and run script
run_script("Install", "uv pip install requests")

# Multi-line script
run_script("Build", """
    set -e
    echo "Building..."
    uv build
    echo "Done"
""")

# Preview script
run_script("Deploy", "...", dry_run=True)
```

**Parameters:**

| Parameter        | Type                  | Default  | Description                    |
| ---------------- | --------------------- | -------- | ------------------------------ |
| `title`          | `str`                 | required | Script title for display       |
| `script`         | `str`                 | required | Multi-line shell script        |
| `echo`           | `bool`                | `True`   | Display script in bordered box |
| `dry_run`        | `bool`                | `False`  | Skip execution                 |
| `capture_output` | `bool`                | `True`   | Capture stdout/stderr          |
| `check`          | `bool`                | `True`   | Raise `typer.Exit` on non-zero |
| `cwd`            | `Path \| str \| None` | `None`   | Working directory              |
| `stream`         | `bool`                | `True`   | Stream output in real-time     |
| `timeout`        | `float \| None`       | `None`   | Timeout in seconds             |

**Key behaviors:**

- Always uses `shell=True` (scripts are shell commands)
- Displays script in bordered box via `console.script_block()` when `echo=True`
- Calls `run()` internally with `echo=False` to prevent double display

#### `run_uv()` - Execute UV Commands

**Location:** `src/bake/ui/run/uv.py`

Run uv commands with "uv" prefix display (not full binary path):

```python
from bake.ui.run import run_uv

# Shows "uv pip install..." + runs
run_uv(["pip", "install", "requests"])

# Silent execution
run_uv(["pip", "install", "requests"], echo=False)

# Preview without running
run_uv(["pip", "install", "requests"], dry_run=True)
```

**Parameters:** Same as `run()`, plus:

- `cmd` is `list[str]` or `tuple[str, ...]` (no string commands)
- `stream` defaults to `False` (uv commands usually don't need streaming)

**Key behaviors:**

- Displays only `"uv"` prefix, not full binary path like `/usr/local/bin/uv`
- Passes `dry_run` through to `run()` for consistent behavior
- Independent `echo` control from `run()`

### Module Structure

```
src/bake/ui/run/
├── __init__.py       # Exports: run, run_script, run_uv, OutputSplitter
├── run.py            # run() with 10 helper functions (refactored for readability)
├── script.py         # run_script() - no docstring (per project policy)
├── uv.py             # run_uv() - no docstring (per project policy)
└── splitter.py       # OutputSplitter class for PTY/stream handling
```

### Error Handling

All functions use `typer.Exit` for clean CLI exits:

```python
# When check=True and command fails
run(["false"])  # Raises typer.Exit(1)

# When check=False
run(["false"], check=False)  # Returns CompletedProcess(returncode=1)
```

### Best Practices

1. **Use `run()` for single commands** - most common case
2. **Use `run_script()` for multi-line scripts** - better display formatting
3. **Use `run_uv()` for uv commands** - cleaner "uv" prefix display
4. **Internal utilities:** Set `echo=False` to avoid spam
5. **User-facing tasks:** Keep `echo=True` (default) for transparency
