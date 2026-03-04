# Publisher Refactoring - Task Checklist

## Phase 1: Create Publisher Module Structure ⏳ NOT STARTED

- [ ] 1.1 Create publisher module
    - Create `src/bakelib/publisher/__init__.py`
    - Create `src/bakelib/publisher/pypi.py`
    - Create `src/bakelib/publisher/crates.py`
    - Acceptance: Module structure created, imports work

## Phase 2: Create Publisher ABC ⏳ NOT STARTED

- [ ] 2.1 Move types to publisher module
    - Move `PublishStatus` enum to `publisher/__init__.py`
    - Move `PublishResult` dataclass to `publisher/__init__.py`
    - Update imports in `space/lib.py`
    - Acceptance: Types moved, imports updated

- [ ] 2.2 Create Publisher abstract base class
    - Define `Publisher` ABC with abstract methods:
        - `_validate_registry()`
        - `_get_publish_token_from_remote()`
        - `_build_for_publish()`
        - `_publish_with_token()`
        - `_is_already_exists_error()`
        - `_is_auth_failure()`
        - `_pre_publish_setup()`
    - Implement `_determine_publish_result()` as template method
    - Acceptance: Publisher ABC created with all abstract methods

## Phase 3: Implement PyPIPublisher ⏳ NOT STARTED

- [ ] 3.1 Create PyPIPublisher class
    - Extract all 7 methods from `PythonLibSpace`
    - Implement PyPI-specific logic
    - Acceptance: PyPIPublisher created with all methods implemented

## Phase 4: Implement CratesPublisher ⏳ NOT STARTED

- [ ] 4.1 Create CratesPublisher class
    - Extract all 7 methods from `RustLibSpace`
    - Implement Crates-specific logic
    - Acceptance: CratesPublisher created with all methods implemented

## Phase 5: Refactor BaseLibSpace ⏳ NOT STARTED

- [ ] 5.1 Remove abstract methods from BaseLibSpace
    - Remove 7 abstract method declarations
    - Keep token caching methods
    - Keep UI methods
    - Keep `_execute_publish()` retry logic
    - Acceptance: BaseLibSpace simplified, no publish abstract methods

## Phase 6: Refactor PythonLibSpace ⏳ NOT STARTED

- [ ] 6.1 Update PythonLibSpace
    - Add `get_publisher()` method returning `PyPIPublisher(self.ctx)`
    - Remove 7 publish method implementations
    - Update `publish()` to use Publisher pattern
    - Acceptance: PythonLibSpace uses PyPIPublisher, tests pass

## Phase 7: Refactor RustLibSpace ⏳ NOT STARTED

- [ ] 7.1 Update RustLibSpace
    - Add `get_publisher()` method returning `CratesPublisher(self.ctx)`
    - Remove 7 publish method implementations
    - Update `publish()` to use Publisher pattern
    - Acceptance: RustLibSpace uses CratesPublisher, tests pass

## Phase 8: Update Tests ⏳ NOT STARTED

- [ ] 8.1 Update unit tests
    - Update tests for Publisher classes
    - Update tests for PythonLibSpace
    - Update tests for RustLibSpace
    - Acceptance: All unit tests pass

- [ ] 8.2 Update integration tests
    - Update any integration tests that use publish
    - Acceptance: All integration tests pass

- [ ] 8.3 Verify test coverage
    - Run coverage report
    - Acceptance: Publisher classes have full coverage

---

## Quick Resume

**Current Phase:** Phase 1 - Create Publisher Module Structure

**Next Task:** 1.1 - Create publisher module

**To start:**

```bash
# Create the module structure
mkdir -p src/bakelib/publisher
touch src/bakelib/publisher/__init__.py
touch src/bakelib/publisher/pypi.py
touch src/bakelib/publisher/crates.py
```

---

## Progress Summary

| Phase     | Status             | Tasks  | Completed |
| --------- | ------------------ | ------ | --------- |
| Phase 1   | ⏳ Not Started     | 1      | 0/1       |
| Phase 2   | ⏳ Not Started     | 2      | 0/2       |
| Phase 3   | ⏳ Not Started     | 1      | 0/1       |
| Phase 4   | ⏳ Not Started     | 1      | 0/1       |
| Phase 5   | ⏳ Not Started     | 1      | 0/1       |
| Phase 6   | ⏳ Not Started     | 1      | 0/1       |
| Phase 7   | ⏳ Not Started     | 1      | 0/1       |
| Phase 8   | ⏳ Not Started     | 3      | 0/3       |
| **Total** | **⏳ Not Started** | **11** | **0/11**  |

---

Last Updated: 2025-03-04
