# Plan: Auto Context Management for BaseSpace Commands

**Last Updated:** 2025-02-07

## Executive Summary

Automatically set `self._ctx = ctx` when `@command` decorated methods are invoked by Typer, eliminating the need for manual `with self._set_ctx(ctx):` context manager usage in command methods.

**Current Problem**: Command methods must manually wrap non-command method calls with `with self._set_ctx(ctx):` boilerplate.

**Proposed Solution**: Wrap command methods during registration in `Bakebook._register_marked_methods()` to automatically set/clear `self._ctx` before/after method invocation.

## Current State Analysis

### How Typer/Click Invokes Commands

From investigation of Typer/Click source code:

1. **Click's Command.invoke()** (`/click/core.py:1255-1270`):

    ```python
    def invoke(self, ctx: Context) -> t.Any:
        if self.callback is not None:
            return ctx.invoke(self.callback, **ctx.params)
    ```

2. **Click's Context.invoke()** (`/click/core.py:768-830`):

    ```python
    def invoke(self, callback, /, *args, **kwargs):
        # ...
        return callback(*args, **kwargs)
    ```

3. **Key Insight**:
    - `ctx.params` contains parsed CLI kwargs (options, arguments)
    - `ctx: Context` parameter is recognized by Click and injected separately
    - For command methods: `callback(self, ctx, **other_cli_params)`

### Current Implementation

**Location**: `src/bake/bakebook/bakebook.py`

```python
def _register_marked_methods(self) -> None:
    for name in method_names:
        bound_method = getattr(self, name)
        cmd_kwargs = self._get_command_kwargs(bound_method)
        if cmd_kwargs:
            self._app.command(**cmd_kwargs)(bound_method)  # <-- Need to wrap here
```

**Location**: `src/bakelib/space/base.py`

```python
class BaseSpace(Bakebook):
    _ctx: Context | None = None

    @property
    def ctx(self) -> Context:
        if self._ctx is None:
            raise RuntimeError("ctx not set - use with _set_ctx() context manager")
        return self._ctx

    @contextmanager
    def _set_ctx(self, ctx: Context):
        self._ctx = ctx
        try:
            yield
        finally:
            self._ctx = None
```

**Current Usage Pattern** (verbose):

```python
@command(help="...")
def my_command(self, ctx: Context) -> None:
    with self._set_ctx(ctx):  # <-- Boilerplate
        self._some_non_command_method()
```

## Proposed Future State

**Desired Usage Pattern** (clean):

```python
@command(help="...")
def my_command(self, ctx: Context) -> None:
    self._some_non_command_method()  # <-- Just works!
```

The wrapping happens automatically during method registration.

## Implementation Plan

### Phase 1: Create Wrapper Function

**Location**: `src/bake/bakebook/bakebook.py`

**Task**: Add `_wrap_command_method()` that:

1. Inspects method signature to verify `ctx` parameter exists
2. Creates wrapper that sets `self._ctx` before calling original method
3. Cleans up `self._ctx` after execution (try/finally)
4. Preserves original function's metadata (`__wrapped__`, etc.)

**Key Implementation Detail**:

```python
import inspect
import functools
import types

def _wrap_command_method(self, method: types.MethodType) -> types.MethodType:
    func = method.__func__
    sig = inspect.signature(func)
    params = list(sig.parameters.values())

    # Check if second parameter is 'ctx: Context'
    has_ctx_param = len(params) >= 2 and params[1].name == 'ctx'

    if not has_ctx_param:
        return method  # No wrapping needed

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # args[0] is self, args[1] is ctx for command methods
        if len(args) >= 2:
            self._ctx = args[1]
        try:
            return func(*args, **kwargs)
        finally:
            self._ctx = None

    return types.MethodType(wrapper, method.__self__)
```

### Phase 2: Integrate Wrapper into Registration

**Task**: Modify `_register_marked_methods()` to wrap command methods:

```python
def _register_marked_methods(self) -> None:
    ...
    for name in method_names:
        try:
            bound_method = getattr(self, name)
        except Exception:
            continue

        if not isinstance(bound_method, types.MethodType):
            continue

        cmd_kwargs = self._get_command_kwargs(bound_method)
        if cmd_kwargs:
            wrapped = self._wrap_command_method(bound_method)  # <-- NEW
            self._app.command(**cmd_kwargs)(wrapped)
```

### Phase 3: Remove Manual `_set_ctx` Usage

**Task**: Clean up existing code to remove manual `with self._set_ctx(ctx):` patterns.

**Files to update**:

- `src/bakelib/space/base.py` - `test()`, `test_integration()`, `test_all()`, `clean()`, `assert_setup_dev()`, `setup_dev()`
- `src/bakelib/space/python.py` - `test()`, `test_all()`, `test_integration()`

**Pattern to remove**:

```python
# Before:
def my_command(self, ctx: Context) -> None:
    with self._set_ctx(ctx):
        self._helper()

# After:
def my_command(self, ctx: Context) -> None:
    self._helper()  # Automatically works!
```

### Phase 4: Deprecate `_set_ctx` (Optional)

**Task**: Keep `_set_ctx` for backward compatibility or edge cases, but document as optional.

**Consider keeping `_set_ctx` for**:

- Manual testing scenarios
- Edge cases where ctx needs to be set without invoking a command
- Backward compatibility with any external usage

## Risk Assessment

### Risks

| Risk                                      | Impact | Mitigation                                    |
| ----------------------------------------- | ------ | --------------------------------------------- |
| Wrapper breaks existing functionality     | High   | Comprehensive test suite + gradual rollout    |
| Signature inspection fails for edge cases | Medium | Add defensive checks + logging                |
| Performance overhead of wrapping          | Low    | Wrapper is minimal (just set/clear attribute) |
| Conflict with other decorators            | Low    | Use `functools.wraps()` to preserve metadata  |

### Edge Cases to Handle

1. **Command methods without `ctx` parameter**: Should not be wrapped
2. **Static methods or class methods**: Should not be wrapped
3. **Already wrapped methods**: Handle gracefully
4. **Inheritance chains**: Ensure wrapper works with overridden methods

## Success Metrics

1. ✅ All existing tests pass without modification
2. ✅ New command methods work without `_set_ctx`
3. ✅ No performance regression in command invocation
4. ✅ `_set_ctx` can still be used manually if needed
5. ✅ Type checking passes (`ty check`)

## Required Resources

- **Files to modify**:
    - `src/bake/bakebook/bakebook.py` (main implementation)
    - `src/bakelib/space/base.py` (cleanup)
    - `src/bakelib/space/python.py` (cleanup)

- **Test files**: Run `bake test` to verify

- **Dependencies**: `inspect`, `functools`, `types` (all stdlib)

## Timeline Estimate

- **Phase 1** (Wrapper function): 30 minutes
- **Phase 2** (Integration): 15 minutes
- **Phase 3** (Cleanup): 30 minutes
- **Phase 4** (Testing): 15 minutes

**Total**: ~1.5 hours

## References

- Click source: `/.venv/lib/python3.14/site-packages/click/core.py`
- Typer source: `/.venv/lib/python3.14/site-packages/typer/core.py`
- Current implementation: `src/bake/bakebook/bakebook.py`
- Context management: `src/bakelib/space/base.py` (BaseSpace class)
