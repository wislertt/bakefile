# SecretUtils - Context

Last Updated: 2026-03-08

## SESSION PROGRESS (2026-03-08)

### ✅ COMPLETED

- Initial planning discussion with user
- Analyzed existing Bakebook architecture
- Analyzed KeyringCache/ChainedCache implementation
- Created dev docs (plan.md, context.md, tasks.md)
- **Phase 1: Nested Command Support - COMPLETE**
- **Phase 2: SecretUtils Class - COMPLETE**
- **Phase 3: BaseLibSpace Integration - COMPLETE**
- **Phase 4: Testing - COMPLETE**
- **Final Verification - COMPLETE**

### All Tasks Done

All 31 tasks completed. Feature is ready for use.

---

## Key Decisions

| Decision                 | Choice                                                | Rationale                                                      |
| ------------------------ | ----------------------------------------------------- | -------------------------------------------------------------- |
| Nested commands          | Required                                              | User preference for `bake secret list` over `bake secret-list` |
| Key tracking             | `get_secret_keys()` method override                   | Keys declared upfront in subclass, not grown dynamically       |
| Default backends         | `[MemoryCache, KeyringCache]`                         | Fast reads from memory, persisted to keyring                   |
| Public API               | `set_secret()`, `get_secret()`, `del_secret()`        | Users need programmatic access, not just CLI                   |
| catch_refresh pattern    | `cache = get_secret_cache(key); @cache.catch_refresh` | Cache object already knows its key                             |
| BaseLibSpace integration | Multiple inheritance                                  | Simpler than composition                                       |

---

## Key Files

### `src/bakelib/utils/secret.py` ✅ COMPLETE

**Purpose:** SecretUtils class for managing cached secrets

**Public API:**

```python
class SecretUtils(Bakebook):
    secret_namespace: str = "bakebook"
    secret_backends: secret_backends_type = DEFAULT_SECRET_BACKENDS  # [MemoryCache, KeyringCache]

    def get_secret_keys(self) -> set[str]:
        """Override in subclass to declare tracked keys."""
        return set()

    def get_secret_cache(self, key: str) -> ChainedCache[str | None]:
        """Get cache object for a key."""

    def get_secret(self, key: str) -> str | None:
        """Get a secret value."""

    def set_secret(self, key: str, value: str) -> None:
        """Set a secret value."""

    def del_secret(self, key: str) -> None:
        """Delete a secret."""

    # CLI commands (in "secret" group):
    @command(name="list", group_name="secret")
    def secret_list(self) -> None: ...

    @command(name="get", group_name="secret")
    def secret_get(self, key: str) -> None: ...

    @command(name="set", group_name="secret")
    def secret_set(self, key: str, value: str) -> None: ...

    @command(name="del", group_name="secret")
    def secret_del(self, key: str | None = None) -> None: ...
```

**Usage pattern for catch_refresh:**

```python
class MySecrets(SecretUtils):
    def get_secret_keys(self) -> set[str]:
        return {"api_key"}

    def fetch_data(self) -> str:
        cache = self.get_secret_cache("api_key")

        @cache.catch_refresh
        def _do_fetch() -> str:
            token = cache.get_value()
            return f"data-with-{token}"

        return _do_fetch()
```

### `src/bake/bakebook/bakebook.py` ✅ COMPLETE

**Purpose:** Base class for all bakefile recipes

**New components:**

- `_get_registered_command_names(app: typer.Typer) -> set[str]` - Helper to extract command names
- `CommandGroup` dataclass with `app: typer.Typer` and computed `registered_commands` property
- `_command_groups: dict[str, CommandGroup]` - Maps group name to CommandGroup
- `_registered_commands` - Computed property reading from `_app.registered_commands`
- `_get_or_create_group(name: str, **kwargs) -> CommandGroup` - Auto-creates group with config
- `_register_command()` - Dispatches to grouped or app command
- `_register_grouped_command()` - Handles group registration
- `_register_app_command()` - Handles main app registration

### `src/bakelib/refreshable_cache/cache.py`

**Purpose:** Cache backends including KeyringCache, MemoryCache, ChainedCache

**Key behaviors:**

- `ChainedCache.get()` - Tries backends in order, returns first hit
- `ChainedCache.set()` - Writes to ALL backends
- `ChainedCache.delete()` - Deletes from ALL backends

### `src/bakelib/space/lib.py`

**Purpose:** BaseLibSpace with publish functionality

**TODO:**

- Add `SecretUtils` to inheritance chain
- Override `get_secret_keys()` to declare publish token keys

---

## Architecture

### Current Inheritance Chain

```
Bakebook
    ↑
CleanUtils
    ↑
BaseSpace
    ↑
BaseLibSpace
```

### Target Inheritance Chain

```
Bakebook
    ↑
CleanUtils
    ↑
BaseSpace
    ↑
SecretUtils (NEW)
    ↑
BaseLibSpace
```

---

## Implementation Notes

### Phase 2: SecretUtils Class (ACTUAL IMPLEMENTATION)

**Key differences from original plan:**

1. **No `_secret_keys` class variable** - Uses `get_secret_keys()` method that returns empty set by default
2. **No `register_key()` method** - Keys declared upfront via `get_secret_keys()` override, not grown dynamically
3. **Methods are public** - `set_secret()`, `get_secret()`, `del_secret()`, `get_secret_cache()` (not prefixed with `_`)
4. **Default backends** - `[MemoryCache, KeyringCache]` not `[KeyringCache, NullCache]`
5. **catch_refresh pattern** - Uses `cache = get_secret_cache(key); @cache.catch_refresh` instead of `@bakebook.catch_refresh(key)`

### Phase 4: Testing (ACTUAL IMPLEMENTATION)

**Test file:** `tests/unit/bakelib/utils/test_secret.py` (18 tests)

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

## Quick Resume

To continue this task:

1. Read this file for current state
2. Read `tasks.md` for remaining work
3. Start with Phase 3 (BaseLibSpace integration)
4. Run `bake lint` and `bake test` after changes

---

## Open Questions

None - all questions resolved in implementation.
