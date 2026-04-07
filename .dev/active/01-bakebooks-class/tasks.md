# Tasks

## 1. Create `EnvBakebooksMeta` and `EnvBakebooks[E]` class

- [ ] 1.1 Create `src/bakelib/environ/env_bakebooks.py`
    - `EnvBakebooksMeta(type)` with `__iter__` — yields `EnvBakebook` instances from `vars(cls)`
    - `EnvBakebooks(Generic[E], metaclass=EnvBakebooksMeta)`
        - `__init_subclass__` — validate attr name == `str(value.env)` for each `EnvBakebook`
        - `get_bakebook(cls, *, ...)` — full signature matching `environ.get_bakebook`, delegates to `get_bakebook(list(cls), ...)`

## 2. Update exports

- [ ] 2.1 Add `EnvBakebooks` to `src/bakelib/environ/__init__.py` (`__all__` + import)

## 3. Tests

- [ ] 3.1 Create `tests/unit/bakelib/environ/test_env_bakebooks.py`
    - Test `__iter__` collects all bakebook instances
    - Test direct attribute access (`Xxx.d`)
    - Test `get_bakebook()` delegates correctly (mock `environ.get_bakebook`)
    - Test `get_bakebook()` signature parity with `environ.get_bakebook`
    - Test validation: matching env code passes
    - Test validation: mismatched env code raises `ValueError` at class creation
    - Test empty class (no bakebooks) — `get_bakebook()` raises appropriate error
