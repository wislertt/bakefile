# Publisher Refactoring - Context

## SESSION PROGRESS (2025-03-04)

### ✅ COMPLETED

- Architecture discussion and refinement
- Key design decisions finalized

### 🟡 IN PROGRESS

- Ready to begin implementation
- Awaiting user confirmation to proceed

### ⚠️ BLOCKERS

- None

---

## Refined Architecture (2025-03-04)

### Key Design Decisions

**1. Publisher holds ctx reference (Option B)**

```python
class PyPIPublisher(Publisher):
    def __init__(self, ctx):
        self.ctx = ctx
        self._dummy_publish_token = "dummy-token-for-dry-run"
```

**2. Space handles token caching; Publisher just publishes (Option B)**

- Space: `_get_cached_publish_token()`, `_execute_publish()` (retry logic)
- Publisher: `_publish_with_token(token, registry)` receives resolved token

**3. Template Method pattern for shared algorithms**

```python
class Publisher(ABC):
    def _determine_publish_result(self, token, result) -> PublishResult:
        # Shared algorithm
        if token is None:
            status = PublishStatus.DRY_RUN
        elif self._is_already_exists_error(result):  # Abstract hook
            status = PublishStatus.ALREADY_EXISTS
        # ...

    @abstractmethod
    def _is_already_exists_error(self, result) -> bool: ...
```

---

## Method Ownership

### BaseLibSpace keeps (Space/infrastructure concerns):

- `_version_bump_context()` - Project state management
- `_get_cached_publish_token()` - Token caching infrastructure
- `_get_token_from_local()` - Config access
- `_handle_publish_result()` - UI/console output
- `publish()` - CLI entry point
- `_execute_publish()` - Retry logic with ChainedCache

### Publisher gets (Platform-specific):

- `_validate_registry()` - Platform registry validation
- `_get_publish_token_from_remote()` - Platform token fetching
- `_build_for_publish()` - Platform build commands
- `_publish_with_token()` - Platform publish commands
- `_is_already_exists_error()` - Platform error detection
- `_is_auth_failure()` - Platform auth errors
- `_pre_publish_setup()` - Platform cleanup
- `_determine_publish_result()` - Template method (uses abstract hooks)

---

## File Structure

```
src/bakelib/
├── publisher/
│   ├── __init__.py        # Publisher ABC, PublishStatus, PublishResult
│   ├── pypi.py            # PyPIPublisher
│   └── crates.py          # CratesPublisher
└── space/
    ├── lib.py             # BaseLibSpace (retains token/UI logic)
    ├── python_lib.py      # PythonLibSpace → returns PyPIPublisher
    └── rust_lib.py        # RustLibSpace → returns CratesPublisher
```

---

## Platform-Specific Details

### PyPIPublisher

- **Registries:** `test-pypi`, `pypi`
- **Build command:** `uv build`
- **Publish command:** `uv publish {dry_run} {index}`
- **Token env:** `UV_PUBLISH_TOKEN`
- **Auth error:** "403 Invalid or non-existent authentication information"
- **Already exists:** "already exists, skipping" or "File already exists"
- **Pre-publish cleanup:** `rm -rf dist`

### CratesPublisher

- **Registries:** `crates`
- **Build command:** _(none - cargo handles compilation)_
- **Publish command:** `cargo publish --allow-dirty {dry_run}`
- **Token env:** `CARGO_REGISTRY_TOKEN`
- **Auth errors:** "status 403 Forbidden" or "status 401 Unauthorized"
- **Already exists:** "already exists on crates.io"
- **Pre-publish cleanup:** `rm -rf target/package`

---

## Quick Resume

### Next Steps:

1. Create `src/bakelib/publisher/` module structure
2. Create `Publisher` ABC with abstract methods
3. Implement `PyPIPublisher` (extract from `PythonLibSpace`)
4. Implement `CratesPublisher` (extract from `RustLibSpace`)
5. Refactor `BaseLibSpace` to use Publisher pattern
6. Update `PythonLibSpace` and `RustLibSpace` to be thin wrappers
7. Update tests
8. Verify all tests pass

### Commands to run:

```bash
# Run tests after changes
bake test

# Run specific test file
uv run pytest tests/unit/bakelib/space/test_python_lib.py -v
```

---

## Key Files Reference

| File                                | Purpose                   | Changes Needed                         |
| ----------------------------------- | ------------------------- | -------------------------------------- |
| `src/bakelib/publisher/__init__.py` | **NEW** - Publisher ABC   | Create                                 |
| `src/bakelib/publisher/pypi.py`     | **NEW** - PyPIPublisher   | Create                                 |
| `src/bakelib/publisher/crates.py`   | **NEW** - CratesPublisher | Create                                 |
| `src/bakelib/space/lib.py`          | BaseLibSpace              | Remove abstract methods, keep token/UI |
| `src/bakelib/space/python_lib.py`   | PythonLibSpace            | Remove 7 methods, add get_publisher()  |
| `src/bakelib/space/rust_lib.py`     | RustLibSpace              | Remove 7 methods, add get_publisher()  |

---

Last Updated: 2025-03-04
