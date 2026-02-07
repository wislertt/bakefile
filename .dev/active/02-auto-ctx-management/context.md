# Context: Auto Context Management for BaseSpace Commands

**Last Updated:** 2025-02-07

## Key Files

### Core Implementation Files

| File                            | Purpose                           | Key Elements                                       |
| ------------------------------- | --------------------------------- | -------------------------------------------------- |
| `src/bake/bakebook/bakebook.py` | Main registration logic           | `_register_marked_methods()`, command registration |
| `src/bakelib/space/base.py`     | BaseSpace class with ctx property | `_ctx`, `ctx` property, `_set_ctx` context manager |
| `src/bakelib/space/lib.py`      | BaseLibSpace extending BaseSpace  | Inherits ctx management from BaseSpace             |
| `src/bakelib/space/python.py`   | PythonSpace with test methods     | Example of current `_set_ctx` usage patterns       |
| `src/bakelib/space/rust.py`     | RustSpace with command methods    | Example of direct ctx.run() usage                  |

### External Dependencies (for reference)

| Path                                                | Purpose                                       |
| --------------------------------------------------- | --------------------------------------------- |
| `/.venv/lib/python3.14/site-packages/click/core.py` | Click's Command.invoke() and Context.invoke() |
| `/.venv/lib/python3.14/site-packages/typer/core.py` | TyperCommand class                            |
| `/.venv/lib/python3.14/site-packages/typer/main.py` | Typer's main entry point                      |

## Key Decisions

### Decision 1: Use Signature Inspection

**Chosen Approach**: Inspect function signature to detect `ctx: Context` parameter

**Alternatives Considered**:

- Rely on `args[1]` → Too fragile, depends on position
- Check parameter name only → Not robust enough
- Use type annotation → Best approach, most reliable

**Rationale**: Signature inspection is explicit, type-safe, and doesn't rely on fragile positional indexing.

### Decision 2: Wrap During Registration

**Chosen Approach**: Wrap in `Bakebook._register_marked_methods()`

**Alternatives Considered**:

- Modify `@command` decorator → Would affect all uses, not just BaseSpace
- Custom TyperCommand class → More complex, harder to maintain
- Metaclass → Overkill, harder to understand

**Rationale**: Registration is the single point where all command methods pass through, making it ideal for cross-cutting concerns.

### Decision 3: Keep `_set_ctx` for Edge Cases

**Chosen Approach**: Keep `_set_ctx` available but de-emphasize in docs

**Rationale**: Provides escape hatch for edge cases while making the common case simpler.

## Current State

### How Commands Are Currently Invoked

```
User runs: bake my-command --option value
         ↓
Typer/Click parses CLI args
         ↓
Click builds ctx.params dict: {"option": "value"}
         ↓
Click injects Context parameter (not in ctx.params)
         ↓
Click calls: my_command(self, ctx, option="value")
```

### Current Boilerplate Pattern

```python
@command(help="Run tests")
def test(self, ctx: Context) -> None:
    with self._set_ctx(ctx):  # <-- Required boilerplate
        self._test(ctx, tests_paths="tests/")
```

### Non-Command Methods Needing ctx

```python
def _test(self, ctx: Context, *, tests_paths: str) -> None:
    # Uses self.ctx.run() internally
    pass
```

## Dependencies

### Technical Dependencies

- `inspect.signature()` - For analyzing method signatures
- `functools.wraps()` - For preserving function metadata
- `types.MethodType` - For working with bound methods

### Code Dependencies

1. **BaseSpace must be imported** for type checking
2. **Bakebook.\_register_marked_methods()** must be modified
3. **All command method tests** must continue passing

## Implementation Notes

### Wrapper Function Design

```python
def _wrap_command_method(self, method: types.MethodType) -> types.MethodType:
    """
    Wrap a command method to automatically set self._ctx before invocation.

    Args:
        method: Bound method from the Bakebook class

    Returns:
        Wrapped bound method that sets/clears self._ctx
    """
    func = method.__func__
    sig = inspect.signature(func)
    params = list(sig.parameters.values())

    # Check if second parameter (after 'self') is named 'ctx'
    has_ctx_param = len(params) >= 2 and params[1].name == 'ctx'

    if not has_ctx_param:
        return method  # No ctx parameter, no wrapping needed

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # For command methods: args = (self, ctx, ...)
        if len(args) >= 2:
            self._ctx = args[1]  # args[1] is the Context parameter
        try:
            return func(*args, **kwargs)
        finally:
            self._ctx = None

    return types.MethodType(wrapper, method.__self__)
```

### Files That Will Change

**Before** (`src/bakelib/space/python.py`):

```python
def test(self, ctx: Context) -> None:
    tests_path = "tests/unit/"
    with self._set_ctx(ctx):
        self._test(ctx, tests_paths=tests_path)
```

**After**:

```python
def test(self, ctx: Context) -> None:
    tests_path = "tests/unit/"
    self._test(ctx, tests_paths=tests_path)  # No _set_ctx needed!
```

## Testing Strategy

1. **Run existing test suite**: `bake test` must pass
2. **Type checking**: `uv run ty check` must pass
3. **Manual testing**: Verify command methods work without `_set_ctx`
4. **Edge case testing**:
    - Command methods without ctx parameter
    - Overridden command methods in subclasses
    - Command methods that call other command methods

## Rollout Plan

1. Implement wrapper function in `bakebook.py`
2. Modify `_register_marked_methods()` to use wrapper
3. Run tests to verify no regression
4. Clean up manual `_set_ctx` usage in space classes
5. Run full test suite again
6. Update documentation if needed
