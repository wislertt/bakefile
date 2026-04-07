# Plan: Add `EnvBakebooks` Container Class

## Goal

Add an `EnvBakebooks[E]` base class to `bakelib/environ/` that groups `EnvBakebook` instances by environment. Users inherit from it, declare bakebook instances as class attributes, and get `get_bakebook()` for free.

## Design

### Metaclass `EnvBakebooksMeta`

- Implements `__iter__` on the class itself (not instances)
- Yields all `EnvBakebook` instances from `vars(cls)` — Pythonic, no private helpers
- Enables `list(Xxx)`, `for bb in Xxx`, etc.

### `EnvBakebooks[E]` base class

- Uses `EnvBakebooksMeta` metaclass (inherited by subclasses automatically)
- `__init_subclass__` validates attribute names match env codes at class definition time
- `get_bakebook()` classmethod with full signature (copied from `environ.get_bakebook`, not `**kwargs`) — type-safe

### Validation

At class creation via `__init_subclass__`:

- For each `EnvBakebook` instance in `vars(cls)`: assert `str(value.env) == attr_name`
- Raise `ValueError` on mismatch (eager, catches mistakes early)

### Signature parity

- `EnvBakebooks.get_bakebook()` signature matches `environ.get_bakebook()` exactly (minus `bakebooks` param)
- Test uses `inspect.signature` to ensure they stay in sync (matches existing pattern in codebase)

## User API

```python
from bakelib.environ import EnvBakebooks

class InPubEgInternetUsC1(EnvBakebooks):
    d1 = D1InPubEgInternetUsC1()  # validated: "d1" == env "d1"
    d = DInPubEgInternetUsC1()
    n = NInPubEgInternetUsC1()
    p = PInPubEgInternetUsC1()
    # get_bakebook() inherited

# Direct access
InPubEgInternetUsC1.d

# Env resolution
InPubEgInternetUsC1.get_bakebook()
```
