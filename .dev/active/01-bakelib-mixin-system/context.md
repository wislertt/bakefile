# Bakelib Mixin System - Context

## Naming Convention (FINAL)

| Concept        | Naming Pattern             | Examples                               |
| -------------- | -------------------------- | -------------------------------------- |
| ABC            | `[Purpose]BaseRecipe`      | `SpaceBaseRecipe`, `ToolBaseRecipe`    |
| Implementation | `[Scope][Purpose]Recipe`   | `PythonSpaceRecipe`, `PreCommitRecipe` |
| Precomposed    | `[Scope][Purpose]Bakebook` | `PythonSpaceBakebook`                  |

**Rationale:**

- Fits "Bakebook" theme (cookbook contains recipes)
- Analogous to Justfile (recipes are tasks)
- `Base` prefix follows Pydantic/Python stdlib convention

---

## Key Files

| File                            | Purpose                         |
| ------------------------------- | ------------------------------- |
| `src/bake/bakebook/__init__.py` | Base `Bakebook` class           |
| `src/bake/cli.py`               | CLI entry point                 |
| `src/bake/decorators.py`        | `@command` decorator            |
| `src/bakelib/`                  | Recipe implementations (new)    |
| `src/bakelib/space/base.py`     | SpaceBaseRecipe ABC             |
| `src/bakelib/space/python.py`   | PythonSpaceRecipe (includes uv) |
| `src/bakelib/space/tools/`      | Space tool recipes              |
| `examples/simple/bakefile.py`   | Example usage                   |

## Key Decisions

### Design Approach

- **Normal OOP**: Standard Python MRO, `super()` for parent access
- **ABC-based**: Use `ABC` with `@abstractmethod` for contracts
- **Explicit requirements**: `__requires__` for recipe dependencies
- **Registry pattern**: Decorator-based registration for discovery
- **Intersection types**: Use `ty.Intersection` for type checking

### Command Merging

- Last recipe in MRO wins
- Users call `super()` to compose behaviors
- No automatic merging or namespacing

### Dependency Validation

- Recipes declare `__requires__ = [OtherRecipe]`
- Validation at class creation time
- Fail fast with clear error messages

### Discovery

- `@register_recipe(name, description)` decorator
- `bake recipes` CLI command to list available recipes
- Registry stores metadata for CLI display

---

## Architecture Notes

### Recipe Integration Points

1. **Command registration** - How recipes add commands to Bakebook
    - `@command` decorator on recipe methods
    - MRO determines which version wins

2. **Property sharing** - How recipes access Bakebook properties
    - Direct access via `self`
    - Recipes can define abstract properties that Bakebook must provide

3. **Context access** - How recipes access `Context` in commands
    - Same as Bakebook: `ctx: Context` parameter

### Class Creation Flow

```python
class MyBakebook(PreCommitRecipe, PythonSpaceRecipe, Bakebook):
    pass
```

Bakebook is the rightmost (top parent), recipes come before.

1. Python builds MRO: `MyBakebook → PreCommitRecipe → PythonSpaceRecipe → Bakebook`
2. Metaclass (if any) validates `__requires__`
3. `@command` decorator registers commands
4. Result: ready-to-use Bakebook with all commands

---

## Constraints

- Must be backward compatible with existing Bakebook usage
- Recipes should be optional - Bakebook works fine without them
- No breaking changes to `@command` decorator or Context API
