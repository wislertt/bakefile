# Bakebook pattern and API

Coding rules live in `CODING_STANDARDS.md`.

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
| `setup_logging()`          | Configure logging from bakebook fields |

**Environment Variable Configuration:**

The `Bakebook` class uses Pydantic's `SettingsConfigDict`:

```python
model_config = SettingsConfigDict(
    env_file=".env",  # Load from .env file
    env_file_encoding="utf-8",  # File encoding
    extra="ignore",  # Ignore extra fields
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

| Property        | Purpose                                                                    |
| --------------- | -------------------------------------------------------------------------- |
| `ctx`           | Access CLI context (run, dry_run, etc.)                                    |
| `bake_log_dict` | Parsed `bake_log` as `dict[str, int]` (e.g., `{"": INFO, "myapp": DEBUG}`) |

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
- Access context features: `ctx.run()`, `ctx.dry_run`, `ctx.verbosity`, `ctx.bakebook`, `ctx.invocation_dir`
- No need to pass `ctx: Context` as a parameter in your command functions

**Context API:**

```python
# Run commands
self.ctx.run("cargo test")
self.ctx.run("bun install", check=False)

# With timeout (raises subprocess.TimeoutExpired if exceeded)
self.ctx.run("rustup update", timeout=60)

# Dry run mode
if self.ctx.dry_run:
    # Handle dry run behavior
    pass

# Override dry run temporarily
with self.ctx.override_dry_run(True):
    # Commands in this block respect the override
    self.ctx.run("echo 'This is a dry run'")

# Verbosity level
self.ctx.verbosity  # 0=silent, 1=WARNING, 2=INFO, 3=DEBUG

# Invocation directory: where `bake` was called from (commands run in the bakefile.py's directory)
self.ctx.invocation_dir
```

---
