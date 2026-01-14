# Module-Level Command Decorator - Context

**Last Updated: 2026-01-04**

---

## SESSION PROGRESS

### ✅ COMPLETED

- Analysis of current Bakebook implementation
- Evaluation of architectural approaches (deferred registration, class decorator, metaclass, post-hoc)
- Selection of recommended approach (deferred registration)
- Creation of implementation plan

### 🟡 IN PROGRESS

- None yet (plan complete, ready to implement)

### ⏳ NOT STARTED

- Phase 1: Create decorator module
- Phase 2: Update Bakebook initialization
- Phase 3: Export from package
- Phase 4: Write tests
- Phase 5: Update documentation

### ⚠️ BLOCKERS

- None

---

## Key Design Decision

**Chosen Approach: Deferred Registration**

The `@bake.command()` decorator stores metadata on the function as attributes. When `Bakebook.__init__` runs, it scans instance methods for these markers and registers them as commands.

**Why this approach:**

- Clean API: `@bake.command()` just works
- Automatic: No manual registration step
- Pythonic: Similar to Flask/FastAPI patterns
- Backwards compatible: Existing API still works

**How it works:**

```python
# During class definition
@command()
def build(self): ...
# -> build._bake_command_kwargs = {}

# During instantiation
bakebook = MyBakebook()
# -> __init__ calls _register_marked_methods()
# -> Scans dir(self), finds _bake_command_kwargs
# -> Registers bound_method with _app
```

---

## Key Files

### `src/bake/bakebook/bakebook.py` (TO MODIFY)

**Current state:**

```python
class Bakebook(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    _app: typer.Typer = PrivateAttr(default_factory=typer.Typer)

    def command(self, *args, **kwargs):
        return self._app.command(*args, **kwargs)
```

**Changes needed:**

1. Add `__init__` method
2. Add `_register_marked_methods()` method

**After changes:**

```python
class Bakebook(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    _app: typer.Typer = PrivateAttr(default_factory=typer.Typer)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._register_marked_methods()

    def _register_marked_methods(self) -> None:
        """Register methods marked with @bake.command as commands."""
        for name in dir(self):
            if name.startswith('_'):
                continue
            attr = getattr(self, name)
            if hasattr(attr, '_bake_command_kwargs'):
                bound_method = getattr(self, name)
                cmd_args = getattr(attr, '_bake_command_args', ())
                cmd_kwargs = getattr(attr, '_bake_command_kwargs', {})
                self._app.command(*cmd_args, **cmd_kwargs)(bound_method)

    def command(self, *args, **kwargs):
        return self._app.command(*args, **kwargs)
```

---

### `src/bake/decorator.py` (TO CREATE)

**New file** containing the `command()` decorator.

**Implementation:**

```python
from typing import Callable

def command(*args, **kwargs) -> Callable:
    """Mark a method as a bakebook command."""
    def decorator(func: Callable) -> Callable:
        func._bake_command_args = args
        func._bake_command_kwargs = kwargs
        return func

    if args and callable(args[0]):
        return decorator(args[0])
    return decorator
```

**Purpose:** Stores decorator metadata on function attributes for later registration.

---

### `src/bake/__init__.py` (TO MODIFY)

**Current state:**

```python
from bake.bakebook.bakebook import Bakebook
from bake.cli.common.context import Context
from bake.cli.utils.version import _get_version

__version__ = _get_version()

__all__ = ["Bakebook", "Context", "__version__"]
```

**Changes needed:**

- Import `command` from `bake.decorator`
- Add to `__all__`

**After changes:**

```python
from bake.bakebook.bakebook import Bakebook
from bake.cli.common.context import Context
from bake.cli.utils.version import _get_version
from bake.decorator import command

__version__ = _get_version()

__all__ = ["Bakebook", "Context", "command", "__version__"]
```

---

### `tests/bake/bakebook/test_bakebook.py` (TO MODIFY)

**Current tests cover:**

- Empty subclass creation
- Field loading from env vars
- Custom methods
- Standalone command registration

**New tests needed:**

- `test_method_command_registration` - Method decorated with `@command()`
- `test_method_has_access_to_self` - Verify `self` works in methods
- `test_custom_command_name` - `@command(name="custom")` works
- `test_inheritance` - Parent/child command behavior
- `test_private_methods_not_registered` - `_private` methods skipped
- `test_hybrid_api` - Both old and new APIs work together

---

### `tests/bake/decorator/test_decorator.py` (TO CREATE)

**New test file** for decorator unit tests.

**Test cases:**

- `test_command_marks_function` - Attributes set correctly
- `test_command_with_no_parens` - `@command` syntax
- `test_command_with_parens` - `@command()` syntax
- `test_command_with_args` - `@command(name="custom")`

---

### `.claude/BEST_PRACTICES.md` (TO MODIFY)

**Section to update:** "Bakebook Pattern"

**Add new subsection** after "Environment Variables with Bakebook":

````markdown
### Class Methods as Commands

Users can define methods as commands with `@bake.command()`:

```python
from bake import Bakebook, command

class MyBakebook(Bakebook):
    database_url: str = "sqlite:///default.db"
    debug: bool = False

    @command()
    def migrate(self):
        """Run migrations - has access to self.database_url"""
        console.echo(f"Migrating {self.database_url}")

    @command(name="deploy-prod")
    def deploy(self):
        """Deploy the application"""
        if self.debug:
            console.echo("Debug mode - skipping deployment")
        else:
            console.echo("Deploying...")

    def helper_method(self):
        """Internal helper - NOT a command"""
        return "internal"

bakebook = MyBakebook()
```
````

**Key points:**

- Methods decorated with `@bake.command()` become CLI commands
- Methods have full access to `self` (instance properties, helper methods)
- Use `@command(name="custom")` for custom command names
- Undecorated methods remain as helper methods (not exposed as commands)

````

---

## Technical Constraints

### Pydantic BaseSettings

The `Bakebook` class inherits from `BaseSettings`, which means:
- `__init__` must call `super().__init__(**kwargs)` for env var loading
- Fields are validated on instantiation
- Environment variables are loaded during initialization

**Implication:** Our `_register_marked_methods()` must happen AFTER `super().__init__()`.

### Typer Command Registration

Commands are registered with the internal Typer app:
- `self._app.command(*args, **kwargs)(func)`
- Typer inspects the function signature
- For methods, we need to pass the **bound method**, not the unbound function

**Implication:** Use `getattr(self, name)` to get the bound method, not the raw function from class dict.

### Private Attr

The `_app` attribute is a Pydantic `PrivateAttr`:
- Not included in `model_dump()`
- Not validated
- Has a default factory

**Implication:** Safe to use for internal state without affecting serialization.

---

## User API Examples

### Basic Usage

```python
from bake import Bakebook, command

class MyBakebook(Bakebook):
    env: str = "dev"

    @command()
    def build(self):
        """Build with access to self.env"""
        console.echo(f"Building for {self.env}")

bakebook = MyBakebook()
````

### With Custom Command Name

```python
class MyBakebook(Bakebook):
    @command(name="deploy-prod")
    def deploy(self):
        """Deploy to production"""
        console.echo("Deploying...")
```

### Accessing Instance Properties

```python
class MyBakebook(Bakebook):
    database_url: str = "sqlite:///default.db"

    @command()
    def migrate(self):
        """Run migrations using self.database_url"""
        console.echo(f"Migrating {self.database_url}")
```

### Helper Methods (Not Commands)

```python
class MyBakebook(Bakebook):
    @command()
    def deploy(self):
        """Deploy - uses helper internally"""
        client = self._get_client()
        client.deploy()

    def _get_client(self):  # No decorator = not a command
        """Internal helper"""
        return DeploymentClient()
```

### Hybrid API (Both Work)

```python
from bake import Bakebook, command

# Old way: standalone functions
bakebook = Bakebook()

@bakebook.command()
def standalone_task():
    """This still works"""
    pass

# New way: class methods
class MyBakebook(Bakebook):
    @command()
    def method_task(self):
        """This is new"""
        pass
```

---

## Related Files

### Current Bakebook Implementation

- `src/bake/bakebook/bakebook.py` - Main class
- `src/bake/bakebook/get.py` - Module loading
- `src/bake/bakebook/__init__.py` - Bakebook package init

### CLI Integration

- `src/bake/cli/bake/main.py` - Main bake CLI
- `src/bake/cli/common/context.py` - Context subclass
- `src/bake/cli/common/obj.py` - BakefileObject

### Existing Examples

- `examples/simple/bakefile.py` - Basic example
- `examples/no_bakebook/bakefile.py` - Example without bakebook

### Documentation

- `.claude/BEST_PRACTICES.md` - Coding standards
- `.claude/PROJECT_KNOWLEDGE.md` - Architecture
- `.claude/CLAUDE.md` - Project overview

---

## Quick Resume

### To continue implementation:

1. **Read the plan** - `.dev/active/14-module-command-decorator/plan.md`
2. **Start with Phase 1** - Create `src/bake/decorator.py`
3. **Run tests** - `make test` after each phase
4. **Check lint** - `make lint` before committing

### Current status:

- **Phase**: Ready to implement
- **Next step**: Create decorator module
- **Estimated time remaining**: ~4 hours

### Testing command:

```bash
# Run all tests
make test

# Run specific test file
pytest tests/bake/bakebook/test_bakebook.py -v

# Run with coverage
make test
```

---

## Important Notes

### Docstring Policy

**DO NOT add docstrings by default.** The developer adds them manually when needed.

See `.claude/BEST_PRACTICES.md` → "Docstring Policy"

### No Automatic Commits

**Do NOT make git commits automatically.** The developer will commit when ready.

See `.claude/CLAUDE.md` → "Key Policies"

### Verification Workflow

1. Make changes
2. Run `make lint` to check code quality
3. Run `make test` to verify tests pass
4. Commit when both pass
