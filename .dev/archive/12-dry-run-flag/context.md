# Dry Run Flag - Context

## SESSION PROGRESS (2025-01-04)

### ✅ COMPLETED

- Phase 1: Core Infrastructure
    - Added `dry_run_option` to params.py (src/bake/cli/common/params.py:64-67)
    - Added `dry_run: bool = False` to BakefileObject (src/bake/cli/common/obj.py:49)
    - Added `dry_run` parameter to `_get_bakefile_object` (src/bake/cli/common/obj.py:130)
    - Added `dry_run` property to Context (src/bake/cli/common/context.py:9-11)
    - Added `_dry_run` parameter to `bake_app_callback` (src/bake/cli/common/app.py:43)
    - Updated imports in app.py and obj.py
    - All linters pass

- Phase 2: Testing
    - Added 3 tests for dry_run flag parsing (tests/bake/cli/common/test_obj.py)
    - Added 3 tests for ctx.dry_run property (tests/bake/cli/common/test_context.py)
    - Added 3 integration tests (tests/bake/cli/bake/test_bake_main.py)
    - All 696 tests pass
    - Coverage: 95%

### 🟡 IN PROGRESS

- None - feature ready for use

### ⏳ TODO

- Phase 3: Documentation (future)

---

## Design Decisions

### 1. Storage Location: BakefileObject (Single Source)

**Decision:** `dry_run` is stored in `BakefileObject.dry_run`

**Rationale:**

- `get_bakefile_object()` creates BakefileObject first
- Must store there due to how the parsing flow works
- Would be complicated to store only in Context

### 2. User Access: ctx.dry_run Property

**Decision:** `Context.dry_run` is a `@property` that returns `self.obj.dry_run`

**Rationale:**

- `dry_run` is user-facing, frequently accessed in user code
- Other params (verbosity, chdir, etc.) are framework-internal
- `ctx.dry_run` is cleaner than `ctx.obj.dry_run` for user code
- Property approach avoids duplication, keeps single source of truth

```python
class Context(typer.Context):
    obj: BakefileObject

    @property
    def dry_run(self) -> bool:
        return self.obj.dry_run
```

### 3. CLI Convention: -n / --dry-run

**Decision:** Short form `-n`, long form `--dry-run`

**Rationale:**

- `-n` is common convention for dry run (make, nix, etc.)
- `--dry-run` is explicit and self-documenting
- Follows familiar CLI patterns

### 4. Scope: Both CLIs

**Decision:** Flag works for both `bake` and `bakefile` CLIs

**Rationale:**

- Consistent user experience
- `bakefile` commands can respect dry run (framework-controlled)
- `bake` commands can access via `ctx.dry_run` (user-controlled)

### 5. Behavior: Skip Execution, Respect Echo Settings

**Decision:** Dry run skips execution, output controlled by verbosity

**Rationale:**

- Dry run controls _behavior_, not _output_
- Verbosity controls _output_
- Clean separation of concerns

---

## Key Files

### bake/cli/common/params.py

**Purpose:** Defines reusable CLI option types

**Relevant:** Need to add `dry_run_option`

**Pattern:**

```python
dry_run_option = Annotated[
    bool,
    typer.Option("-n", "--dry-run", help="...")
]
```

### bake/cli/common/obj.py

**Purpose:** BakefileObject dataclass and parsing logic

**Relevant:**

- Add `dry_run: bool = False` to `BakefileObject`
- Add `dry_run` param to `_get_bakefile_object`
- Pass `dry_run` to BakefileObject constructor

**Key Functions:**

- `_get_bakefile_object()` - Hidden typer command that parses args
- `get_bakefile_object()` - Calls \_get_bakefile_object via typer

### bake/cli/common/context.py

**Purpose:** Custom typer.Context with typed obj

**Relevant:** Add `@property def dry_run` to Context class

**Current State:**

```python
class Context(typer.Context):
    obj: BakefileObject
```

**After:**

```python
class Context(typer.Context):
    obj: BakefileObject

    @property
    def dry_run(self) -> bool:
        return self.obj.dry_run
```

### bake/cli/common/app.py

**Purpose:** BakefileApp and bake_app_callback

**Relevant:** Add `_dry_run` param to `bake_app_callback`

**Key Function:**

```python
def bake_app_callback(
    ctx: Context,
    _chdir: chdir_option = ...,
    _file_name: file_name_option = ...,
    _bakebook_name: bakebook_name_option = ...,
    _version: version_option = False,
    _is_chain_commands: is_chain_commands_option = None,
    _verbosity: verbosity_option = 0,
    _dry_run: dry_run_option = False,  # NEW
):
    ctx.obj = obj
    show_help_if_no_command(ctx)
```

**Note:** Parameter needed for Typer to parse flag, but value already set in obj by `get_bakefile_object()`

### bake/cli/bake/main.py

**Purpose:** Entry point for `bake` CLI

**Relevant:** Uses `bake_app_callback_with_obj`, automatically gets dry_run support

**No changes needed** - works via callback

### bake/cli/bakefile/main.py

**Purpose:** Entry point for `bakefile` CLI

**Relevant:** Uses `bake_app_callback_with_obj`, automatically gets dry_run support

**No changes needed** - works via callback

---

## Parameter Flow

```
CLI: bake -n hello
     ↓
get_bakefile_object()
     ↓
_parse args via typer
     ↓
_get_bakefile_object(..., dry_run=True)
     ↓
BakefileObject(..., dry_run=True)
     ↓
bake_app_callback_with_obj(obj)
     ↓
bake_app_callback(ctx, ..., _dry_run=True)
     ↓
ctx.obj = obj (obj.dry_run already set)
     ↓
User code accesses ctx.dry_run → returns ctx.obj.dry_run
```

---

## Testing Strategy

1. **Unit tests for dry_run option:**
    - Default value is `False`
    - `-n` sets to `True`
    - `--dry-run` sets to `True`

2. **Property test:**
    - `ctx.dry_run` returns `ctx.obj.dry_run`

3. **Integration test:**
    - Create bakefile with command checking `ctx.dry_run`
    - Verify behavior with and without flag

---

## Quick Resume

To implement this feature:

1. Read `plan.md` for full strategy
2. Follow Phase 1 tasks in order:
    - Add `dry_run_option` to params.py
    - Add `dry_run` to BakefileObject
    - Add `dry_run` to `_get_bakefile_object`
    - Add `dry_run` property to Context
    - Add `_dry_run` to `bake_app_callback`
3. Update imports
4. Run `make lint` and `make test`
5. Check `tasks.md` for remaining work

---

## Related Files

- `src/bake/ui/run.py` - run() function (future: may add dry_run param)
- `src/bake/ui/run_script.py` - run_script() function (future: may add dry_run param)
- Test files in `tests/bake/cli/common/`

---

## Last Updated: 2025-01-04
