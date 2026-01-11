# Bakelib Mixin System - Context

## Key Insight

**No separate "Recipe" or "Mixin" concept needed.** Everything inherits from `Bakebook` directly. Multiple inheritance provides composition.

---

## Naming Convention (FINAL)

| Concept     | Naming Pattern     | Examples                             |
| ----------- | ------------------ | ------------------------------------ |
| Base class  | `[Purpose]`        | `PythonSpace`, `PreCommit`, `Docker` |
| Precomposed | `[Scope][Purpose]` | `PythonProject`                      |

**Rationale:**

- Simple: no "Recipe", "Mixin", "BaseRecipe" terminology
- Everything is a Bakebook subclass
- Composition via standard Python multiple inheritance
- MRO determines behavior (leftmost parent wins for conflicts)

---

## Key Files

| File                            | Purpose                        |
| ------------------------------- | ------------------------------ |
| `src/bake/bakebook/__init__.py` | Base `Bakebook` class          |
| `src/bake/cli.py`               | CLI entry point                |
| `src/bake/decorators.py`        | `@command` decorator           |
| `src/bakelib/`                  | Bakebook implementations (new) |
| `src/bakelib/space/python.py`   | PythonSpace (lint, test, uv)   |
| `src/bakelib/space/rust.py`     | RustSpace (cargo clippy, test) |
| `src/bakelib/tools/`            | Tool Bakebooks                 |
| `examples/simple/bakefile.py`   | Example usage                  |

---

## Key Decisions

### Design Approach

- **Standard Python OOP**: Normal MRO, `super()` for parent access
- **No ABC required**: Optional, use if contract needed
- **No `__requires__`**: Multiple inheritance handles dependencies
- **No registry**: Direct import, simpler discovery

### Command Merging

- Leftmost parent in inheritance list wins (MRO)
- Users call `super()` to compose behaviors
- No automatic merging or namespacing

### Conflict Resolution

- **Field conflicts**: Leftmost parent wins (Pydantic field merging)
- **Command conflicts**: Leftmost parent wins (Python MRO)
- Method override without `@command` loses registration
- Method override with `@command` replaces parent registration

### Discovery

- Direct import: `from bakelib.space import PythonSpace`
- Optional: `bake recipes` CLI command for listing available classes

---

## Architecture Notes

### Bakebook Composition

1. **Command registration** - How Bakebook subclasses add commands
    - `@command` decorator on methods
    - MRO determines which version wins

2. **Property sharing** - How subclasses access Bakebook properties
    - Direct access via `self`
    - Pydantic field merging via multiple inheritance

3. **Context access** - How commands access `Context`
    - Same as Bakebook: `ctx: Context` parameter

### Class Creation Flow

```python
class MyBakebook(PreCommit, PythonSpace, Bakebook):
    pass
```

MRO: `MyBakebook → PreCommit → PythonSpace → Bakebook`

1. Python builds MRO using C3 linearization
2. Pydantic merges fields (leftmost wins for conflicts)
3. `@command` decorator registers commands (leftmost wins for conflicts)
4. Result: ready-to-use Bakebook with all commands

---

## Multiple Inheritance Behaviors (Tested)

See `tests/bake/bakebook/test_inheritance.py` for comprehensive tests.

### MRO Order Effects

```python
class LeftFirst(LeftBakebook, RightBakebook, Bakebook):
    pass  # Left wins

class RightFirst(RightBakebook, LeftBakebook, Bakebook):
    pass  # Right wins
```

### Field/Command Conflicts

- Same field name: leftmost parent's value wins
- Same command name: leftmost parent's command wins
- Only one command registered (not both)

### Deep Inheritance Chains

```python
class Level1(Bakebook): ...
class Level2(Level1): ...
class Level3(Level2): ...
class FinalBakebook(Level3): pass  # Gets all fields/commands
```

### Method Override Behavior

- **Override without `@command`**: Loses parent's command registration
- **Override with `@command`**: Replaces parent's command registration

### Diamond Inheritance

```python
    A
   / \
  B   C
   \ /
    D
```

Base class `A` appears only once in MRO (C3 linearization).

---

## Constraints

- Must be backward compatible with existing Bakebook usage
- Bakelib classes should be optional - Bakebook works fine without them
- No breaking changes to `@command` decorator or Context API
