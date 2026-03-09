# SecretUtils - Task Checklist

Last Updated: 2026-03-08

## Phase 1: Nested Command Support ✅ COMPLETE

- [x] 1.1 Add `group_name` parameter to `@command` decorator
    - File: `src/bake/bakebook/decorator.py`
    - Acceptance: Parameter stored in `CommandKwargs`
- [x] 1.2 Add `CommandGroup` dataclass to wrap `typer.Typer`
    - File: `src/bake/bakebook/bakebook.py`
    - Acceptance: Has `app: typer.Typer` and computed `registered_commands` property
- [x] 1.3 Add `_get_registered_command_names()` helper function
    - Acceptance: Extracts command names from Typer app
- [x] 1.4 Add `_command_groups: dict[str, CommandGroup]` to Bakebook
    - Acceptance: Maps group name to CommandGroup
- [x] 1.5 Make `_registered_commands` a computed property
    - Acceptance: Reads from `_app.registered_commands` (single source of truth)
- [x] 1.6 Add `_get_or_create_group()` method with `**kwargs` support
    - Acceptance: Auto-creates group, accepts help text etc.
- [x] 1.7 Refactor `_register_marked_methods()` into smaller methods
    - Acceptance: Split into `_register_command()`, `_register_grouped_command()`, `_register_app_command()`
- [x] 1.8 Test nested command group manually
    - Acceptance: `bake --help` shows nested group

## Phase 2: SecretUtils Class ✅ COMPLETE

- [x] 2.1 Create `src/bakelib/utils/secret.py` with SecretUtils class
    - Acceptance: File created with basic class structure
- [x] 2.2 Implement `__init__` with group creation
    - Acceptance: `_get_or_create_group("secret", help="...")` called
- [x] 2.3 Implement `secret list` command with `@command(group_name="secret")`
    - Acceptance: Lists tracked keys with cache status
- [x] 2.4 Implement `secret get` command
    - Signature: `bake secret get <key>`
    - Acceptance: Returns value from keyring
- [x] 2.5 Implement `secret set` command
    - Signature: `bake secret set <key> <value>`
    - Acceptance: Sets value in keyring
- [x] 2.6 Implement `secret del` command
    - Signature: `bake secret del [<key>]` (no arg = delete all tracked)
    - Acceptance: Deletes by key or all tracked keys
- [x] 2.7 Implement `get_secret_keys()` method (override in subclass)
    - Acceptance: Returns empty set by default, override to declare keys

## Phase 3: BaseLibSpace Integration ✅ COMPLETE

- [x] 3.1 Add SecretUtils to BaseLibSpace inheritance
    - File: `src/bakelib/space/lib.py`
    - Acceptance: `class BaseLibSpace(SecretUtils, BaseSpace)`
- [x] 3.2 Update `bakefile.py` to not duplicate SecretUtils inheritance
    - Acceptance: `class MyBakebook(PythonLibSpace)` (SecretUtils via BaseLibSpace)
- [x] 3.3 Verify commands work from BaseLibSpace subclass
    - Acceptance: `bake secret list` works

## Phase 4: Testing ✅ COMPLETE

- [x] 4.1 Create test file `tests/unit/bakelib/utils/test_secret.py`
- [x] 4.2 Test `@command(group_name=...)` routes correctly
- [x] 4.3 Test `_get_or_create_group()` creates on-demand
- [x] 4.4 Test `secret list` lists tracked keys
- [x] 4.5 Test `secret get/set/del` with keyring
- [x] 4.6 Test delete all tracked keys (no argument)
- [x] 4.7 Test `get_secret_keys()` override
- [x] 4.8 Test `@cache.catch_refresh` decorator pattern in subclass method
- [x] 4.9 Test `ChainedCache.set()` writes to all backends
- [x] 4.10 Run full test suite: `bake test`

## Final Verification ✅ COMPLETE

- [x] All 1524 unit tests pass
- [x] Type check passes (`ty check`)
- [x] CLI shows secret command with help text

---

## Progress Summary

| Phase     | Status   | Tasks Done |
| --------- | -------- | ---------- |
| Phase 1   | ✅       | 8/8        |
| Phase 2   | ✅       | 7/7        |
| Phase 3   | ✅       | 3/3        |
| Phase 4   | ✅       | 10/10      |
| Final     | ✅       | 3/3        |
| **Total** | **100%** | **31/31**  |
