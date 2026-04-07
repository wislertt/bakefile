# Context

## Key Files

| File                                               | Role                                                                     |
| -------------------------------------------------- | ------------------------------------------------------------------------ |
| `src/bakelib/environ/env_bakebooks.py`             | **New** — `EnvBakebooksMeta` + `EnvBakebooks[E]`                         |
| `src/bakelib/environ/__init__.py`                  | Export `EnvBakebooks`                                                    |
| `src/bakelib/environ/get_bakebook.py`              | Existing `get_bakebook()` — `EnvBakebooks.get_bakebook()` delegates here |
| `src/bakelib/environ/bakebook.py`                  | Existing `EnvBakebook` — type check target for collection                |
| `tests/unit/bakelib/environ/test_env_bakebooks.py` | **New** — tests for `EnvBakebooks`                                       |

## Existing Patterns

- Signature parity tests: `inspect.signature()` comparison (see `tests/unit/bake/bakebook/utils.py`, `tests/unit/bake/ui/test_console.py`)
- `__init_subclass__` for validation: already used in `BaseEnv._FrozenEnvMeta` pattern
- Generic `E = TypeVar("E", bound=EnvBakebook)`: defined in `get_bakebook.py`

## Decisions

- **Collection scope**: `vars(cls)` only — no MRO walk (matches pattern where all bakebooks declared directly)
- **Validation**: eager at class creation via `__init_subclass__` — attr name must equal `str(env)`
- **Iteration**: metaclass `__iter__` — Pythonic, no private `_collect_bakebooks` helper
- **Signature**: full copy of `get_bakebook` params (not `**kwargs`) — type-safe
