# SecretUtils Implementation Plan

Last Updated: 2026-03-08

## Executive Summary

Add `SecretUtils` class to bakefile - a Bakebook subclass that provides commands for managing cached secrets in the system keyring. This enables users to inspect, set, and delete cached tokens/secrets via CLI commands like `bake secret list`, `bake secret get <key>`, etc.

**Key Features:**

- Nested command group (`bake secret <subcommand>`)
- Track registered secret keys via `get_secret_keys()` method override
- Public API for programmatic access (`set_secret()`, `get_secret()`, `del_secret()`)
- `@cache.catch_refresh` decorator pattern for retry on auth failure
- Integration with `BaseLibSpace` for automatic key tracking

---

## Current State Analysis

### Existing Architecture

1. **Bakebook** (`src/bake/bakebook/bakebook.py`)
    - Base class for all bakefile recipes
    - Has `_app: typer.Typer` for command registration
    - Uses `@command` decorator to mark methods as CLI commands
    - ✅ Supports nested command groups via `_get_or_create_group()`

2. **KeyringCache** (`src/bakelib/refreshable_cache/cache.py`)
    - Uses `namespace` + `key` for storage via `keyring` library
    - `set()`, `delete()`, `get_value()` methods available
    - `ChainedCache` chains multiple backends

3. **BaseLibSpace** (`src/bakelib/space/lib.py`)
    - Extends `BaseSpace` → `CleanUtils` → `Bakebook`
    - Uses `ChainedCache` with keys like `publish-token-{registry}`
    - Namespace is `self._package_name`

---

## Proposed Future State

### New Components

1. ✅ **Bakebook nested commands** - Done via `_get_or_create_group(name, **kwargs)`
2. ✅ **SecretUtils** - New Bakebook subclass with `bake secret *` commands
3. ⏳ **BaseLibSpace integration** - Automatic SecretUtils inclusion

### Command Structure

```
bake
├── secret (command group)
│   ├── list      # List tracked keys and their cache status
│   ├── get       # Get a secret value by key
│   ├── set       # Set a secret value
│   └── del       # Delete a secret (by key or all tracked)
└── ...existing commands
```

---

## Implementation Phases

### Phase 1: Nested Command Support ✅ COMPLETE

**Files modified:**

- `src/bake/bakebook/decorator.py` - Added `group_name` parameter
- `src/bake/bakebook/bakebook.py` - Added `CommandGroup` dataclass, refactored registration

**Acceptance:** ✅

- `@command(name="list", group_name="secret")` works
- Group auto-created on first use
- Group appears in `--help` output

---

### Phase 2: SecretUtils Class ✅ COMPLETE

**File:** `src/bakelib/utils/secret.py`

**Actual Implementation:**

```python
from collections.abc import Callable
from typing import Annotated

import typer
from pydantic import Field

from bake import Bakebook, command, console
from bakelib.refreshable_cache import ChainedCache, KeyringCache, MemoryCache, RefreshableCache

SECRET_GROUP = "secret"
DEFAULT_SECRET_BACKENDS: list[type[RefreshableCache]] = [MemoryCache, KeyringCache]

secret_backends_type = Annotated[list[type[RefreshableCache]], Field(exclude=True, repr=False)]


class SecretUtils(Bakebook):
    """Manage cached secrets in system keyring."""

    secret_namespace: str = "bakebook"
    secret_backends: secret_backends_type = DEFAULT_SECRET_BACKENDS

    def get_secret_keys(self) -> set[str]:
        """Override in subclass to declare tracked keys."""
        return set()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._get_or_create_group(SECRET_GROUP, help="Manage cached secrets")

    def _get_fetch_fn(self, key: str) -> Callable[[], str | None]:
        def null_fetch_fn() -> str | None:
            return None
        return null_fetch_fn

    def get_secret_cache(self, key: str) -> ChainedCache[str | None]:
        """Get a ChainedCache instance for a secret key."""
        return ChainedCache(
            backends=self.secret_backends,
            namespace=self.secret_namespace,
            key=key,
            fetch_fn=self._get_fetch_fn(key),
        )

    @command(name="list", group_name=SECRET_GROUP)
    def secret_list(self) -> None:
        """List all tracked keys with their cache status."""
        ...

    def get_secret(self, key: str) -> str | None:
        """Get a secret value."""
        cache = self.get_secret_cache(key)
        return cache.get_value()

    def set_secret(self, key: str, value: str) -> None:
        """Set a secret value."""
        cache = self.get_secret_cache(key)
        cache.set(value)

    def del_secret(self, key: str) -> None:
        """Delete a secret."""
        cache = self.get_secret_cache(key)
        cache.delete()

    @command(name="get", group_name=SECRET_GROUP)
    def secret_get(self, key: Annotated[str, typer.Argument()]) -> None: ...

    @command(name="set", group_name=SECRET_GROUP)
    def secret_set(self, key: Annotated[str, typer.Argument()], value: Annotated[str, typer.Argument()]) -> None: ...

    @command(name="del", group_name=SECRET_GROUP)
    def secret_del(self, key: Annotated[str | None, typer.Argument()] = None) -> None: ...
```

**Key differences from original plan:**

| Original Plan                      | Actual Implementation                                 | Rationale                                    |
| ---------------------------------- | ----------------------------------------------------- | -------------------------------------------- |
| `_secret_keys: ClassVar[set[str]]` | `get_secret_keys() -> set[str]`                       | Method override is cleaner                   |
| `register_key()` classmethod       | Not needed                                            | Keys declared upfront, not grown dynamically |
| `@bakebook.catch_refresh(key)`     | `cache = get_secret_cache(key); @cache.catch_refresh` | Cache already knows its key                  |
| Methods prefixed with `_`          | Public methods                                        | Users need programmatic access               |
| `[KeyringCache, NullCache]`        | `[MemoryCache, KeyringCache]`                         | Fast reads, persisted writes                 |

---

### Phase 3: BaseLibSpace Integration ⏳ NOT STARTED

**File:** `src/bakelib/space/lib.py`

```python
from bakelib.utils.secret import SecretUtils

class BaseLibSpace(SecretUtils, BaseSpace):
    def get_secret_keys(self) -> set[str]:
        return {f"publish-token-{registry}" for registry in self._registries}
```

---

### Phase 4: Testing ✅ COMPLETE

**File:** `tests/unit/bakelib/utils/test_secret.py` (18 tests)

**Test coverage:**

- `TestSecretUtilsInit` - Group creation, namespace default
- `TestSecretList` - List tracked keys with cache status
- `TestSecretGet` - Get secret value
- `TestSecretSet` - Set secret, warn for unregistered key
- `TestSecretDel` - Delete single key, delete all tracked
- `TestGetSecretKeys` - Default empty, override in subclass
- `TestGetSecretCache` - Creates ChainedCache with correct params
- `TestSecretMethods` - set/get/del work together
- `TestCatchRefresh` - Decorator pattern, retry on error, use in subclass method

---

## Risk Assessment

| Risk                                | Likelihood | Impact | Mitigation                                       |
| ----------------------------------- | ---------- | ------ | ------------------------------------------------ |
| Keyring backend varies by OS        | Medium     | Medium | Test on multiple backends, document requirements |
| Key namespace conflicts             | Low        | High   | Use package name as namespace                    |
| Breaking existing Bakebook behavior | Low        | High   | Only add new method, don't modify existing       |

---

## Dependencies

- `keyring` library (already installed)
- `typer` (already installed)
- No new external dependencies
