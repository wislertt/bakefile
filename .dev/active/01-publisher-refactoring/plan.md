# Publisher Refactoring - Implementation Plan

## Executive Summary

Extract platform-specific publishing logic from `PythonLibSpace` and `RustLibSpace` into dedicated `Publisher` classes using the Template Method pattern.

**Problem:** `PythonLibSpace` and `RustLibSpace` have nearly identical method structures (7 methods each) with only platform-specific details differing. Hybrid publish scenarios require overriding all 7 methods.

**Solution:** Create `Publisher` ABC with platform-specific subclasses (`PyPIPublisher`, `CratesPublisher`). Space classes become thin wrappers that delegate to Publisher.

---

## Architecture Decision Summary

### Decision 1: Publisher holds reference to ctx

```python
class PyPIPublisher(Publisher):
    def __init__(self, ctx):  # Option B
        self.ctx = ctx
```

### Decision 2: Space handles token caching, Publisher just publishes

```python
# Space keeps:
- _get_cached_publish_token()
- _get_token_from_local()
- _execute_publish()  # retry logic

# Publisher receives token:
def _publish_with_token(self, token: str | None, registry: str) -> PublishResult
```

### Decision 3: Template Method pattern for shared algorithm

```python
class Publisher(ABC):
    def _determine_publish_result(self, token, result) -> PublishResult:
        # Shared algorithm in base class
        if token is None:
            status = PublishStatus.DRY_RUN
        elif self._is_already_exists_error(result):  # Abstract hook
            status = PublishStatus.ALREADY_EXISTS
        # ...
```

---

## Method Classification

### STAYS in BaseLibSpace (Space concerns)

| Method                      | Reason                                    |
| --------------------------- | ----------------------------------------- |
| `_version_bump_context`     | Modifies `self._version`, project state   |
| `_get_cached_publish_token` | Token caching infrastructure              |
| `_get_token_from_local`     | Accesses `self.bake_publish_token` config |
| `_handle_publish_result`    | UI/console output                         |
| `publish` (CLI method)      | Entry point, CLI discoverability          |
| `_execute_publish`          | Retry logic with ChainedCache             |

### MOVES to Publisher (Platform-specific)

| Method                           | PyPI                      | Crates                        |
| -------------------------------- | ------------------------- | ----------------------------- |
| `_validate_registry`             | test-pypi, pypi           | crates                        |
| `_get_publish_token_from_remote` | PyPI token source         | Crates token source           |
| `_build_for_publish`             | `uv build`                | _(none)_                      |
| `_publish_with_token`            | `uv publish`              | `cargo publish`               |
| `_is_already_exists_error`       | "already exists" messages | "already exists on crates.io" |
| `_is_auth_failure`               | 403 Invalid auth          | 403/401 status                |
| `_pre_publish_setup`             | `rm -rf dist`             | `rm -rf target/package`       |

### STAYS in Publisher ABC (Template method)

| Method                      | Reason                                 |
| --------------------------- | -------------------------------------- |
| `_determine_publish_result` | Shared algorithm, calls abstract hooks |

---

## File Structure

```
src/bakelib/
├── publisher/
│   ├── __init__.py        # Publisher ABC, PublishStatus, PublishResult
│   ├── pypi.py            # PyPIPublisher
│   └── crates.py          # CratesPublisher
└── space/
    ├── lib.py             # BaseLibSpace (simplified)
    ├── python_lib.py      # PythonLibSpace (thin wrapper)
    └── rust_lib.py        # RustLibSpace (thin wrapper)
```

---

## Refactored Flow

### Before (current):

```python
class PythonLibSpace(BaseLibSpace):
    def _validate_registry(self, registry: str) -> PyPIRegistry:
        # 7 platform-specific methods implemented here
```

### After:

```python
class PythonLibSpace(PythonSpace, BaseLibSpace):
    def get_publisher(self) -> PyPIPublisher:
        return PyPIPublisher(self.ctx)

    @command
    def publish(self, registry, token, version):
        publisher = self.get_publisher()
        cached_token = self._get_cached_publish_token(token, registry)

        console.start(f"Publishing to {registry}")
        publisher._pre_publish_setup()

        with self._version_bump_context(version):
            publisher._build_for_publish()
            result = self._execute_publish(cached_token, registry, publisher)

        self._handle_publish_result(result)
```

---

## Implementation Phases

### Phase 1: Create Publisher Module Structure

- Create `src/bakelib/publisher/__init__.py`
- Create `src/bakelib/publisher/pypi.py`
- Create `src/bakelib/publisher/crates.py`

### Phase 2: Create Publisher ABC

- Move `PublishStatus` enum to publisher module
- Move `PublishResult` dataclass to publisher module
- Create `Publisher` ABC with abstract methods
- Implement `_determine_publish_result` as template method

### Phase 3: Implement PyPIPublisher

- Extract all 7 methods from `PythonLibSpace`
- Implement PyPI-specific logic

### Phase 4: Implement CratesPublisher

- Extract all 7 methods from `RustLibSpace`
- Implement Crates-specific logic

### Phase 5: Refactor PythonLibSpace

- Remove 7 method implementations
- Add `get_publisher()` method
- Update `publish()` to use Publisher

### Phase 6: Refactor RustLibSpace

- Remove 7 method implementations
- Add `get_publisher()` method
- Update `publish()` to use Publisher

### Phase 7: Update BaseLibSpace

- Remove abstract methods (now in Publisher)
- Keep token caching, UI, version bumping
- Update `publish()` to work with Publisher pattern

### Phase 8: Update Tests

- Update unit tests for new Publisher classes
- Update integration tests
- Verify all tests pass

---

## Success Criteria

1. **Hybrid publish requires 1 method override** instead of 7
2. **All tests pass** after refactoring
3. **Publisher classes independently testable**
4. **No breaking changes** for existing bakefiles

---

Last Updated: 2025-03-04
