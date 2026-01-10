# Bakelib Mixin System - Plan

## Overview

Design and implement an extension system (`src/bakelib/`) that provides recipes for `Bakebook`. These recipes add pre-built commands and functionality to bakefiles.

**Naming Convention:**

- `*BaseRecipe` = ABC (e.g., `SpaceBaseRecipe`)
- `*Recipe` = Implementation (e.g., `PythonSpaceRecipe`)
- `*Bakebook` = Precomposed (e.g., `PythonSpaceBakebook`)

## High-Level Requirements

### 1. Core Recipe ABC

Define an ABC that establishes a contract for "project space" functionality:

```python
from abc import ABC, abstractmethod

class SpaceBaseRecipe(ABC):
    """ABC defining standard bake commands for a project type."""

    @abstractmethod
    def bake_lint(self) -> None: ...

    @abstractmethod
    def bake_test(self) -> None: ...
```

**Purpose:** Any class implementing this ABC gains standardized `bake lint` and `bake test` commands.

### 2. Language-Specific Space Implementations

Concrete implementations of the Space ABC for different languages:

- **PythonSpaceRecipe**: `ruff` for lint, `pytest` for test, includes uv commands
- **RustSpaceRecipe**: `cargo clippy` for lint, `cargo test` for test
- **JavaScriptSpaceRecipe**: `eslint` for lint, `vitest/jest` for test

### 3. Tool Recipes

Composable recipes for specific tools/workflows:

- **PreCommitRecipe**: Adds `bake setup-precommit`, `bake run-precommit`
- **DockerRecipe**: Adds docker commands

### 4. Usage Pattern

Users compose recipes with their `Bakebook`:

```python
from bake import Bakebook
from bakelib.space import PythonSpaceRecipe, PreCommitRecipe

class MyBakebook(PreCommitRecipe, PythonSpaceRecipe, Bakebook):
    # Bakebook last (top parent), recipes before
    pass
```

This automatically provides:

- `bake lint` (from PythonSpaceRecipe → ruff)
- `bake test` (from PythonSpaceRecipe → pytest)
- `bake install` (from PythonSpaceRecipe → uv)
- `bake setup-precommit` (from PreCommitRecipe)
- `bake run-precommit` (from PreCommitRecipe)

---

## Decisions

### Q1: Protocol vs ABC

**Decision: ABC**

Use `ABC` with `@abstractmethod` for explicit inheritance and clearer intent. Can provide base implementations where needed.

---

### Q2: Command Merging Strategy

**Decision: Normal OOP (MRO-based)**

Standard Python Method Resolution Order. Leftmost in inheritance list wins (most derived). Rightmost is top parent (most base). Child class can call `super()` to access parent implementations.

```python
class MyBakebook(PreCommitRecipe, PythonSpaceRecipe, Bakebook):
    pass
# MRO: MyBakebook → PreCommitRecipe → PythonSpaceRecipe → Bakebook
```

---

### Q3: Conflict Resolution

**Decision: Later recipe wins, user calls super() if needed**

If two recipes define the same command, the later one in MRO wins. Users who want both behaviors explicitly call `super()`.

```python
def bake_install(self):
    super().bake_install()  # Call PreCommitRecipe's version
    # Add custom behavior
```

---

### Q4: Recipe Dependencies

**Decision: Explicit requirements with validation**

Recipes declare `__requires__` and validation happens at class creation time.

```python
class PreCommitRecipe:
    __requires__ = [PythonSpaceRecipe]  # Must be in inheritance chain
```

Validation on class creation:

```python
class MyBakebook(Bakebook, PreCommitRecipe):  # Missing PythonSpaceRecipe!
    pass
# Error: PreCommitRecipe requires PythonSpaceRecipe but it's not in the inheritance chain
```

---

### Q5: Discovery API

**Decision: Registry pattern with CLI command**

#### Registry Design

```python
# bakelib/registry.py
from collections.abc import Callable
from typing import Any

class RecipeRegistry:
    _recipes: dict[str, type] = {}

    @classmethod
    def register(cls, name: str, description: str = "") -> Callable[[type], type]:
        """Decorator to register a recipe."""
        def decorator(recipe_cls: type) -> type:
            cls._recipes[name] = {
                "class": recipe_cls,
                "description": description,
            }
            return recipe_cls
        return decorator

    @classmethod
    def list_all(cls) -> dict[str, dict]:
        """Return all registered recipes."""
        return cls._recipes.copy()

# Usage in recipes:
@register_recipe("python-space", description="Python project with ruff + pytest + uv")
class PythonSpaceRecipe(SpaceBaseRecipe): ...
```

#### CLI Command

```bash
$ bake recipes
Available recipes:
  python-space    Python project with ruff + pytest + uv
  rust-space      Rust project with cargo clippy + test
  precommit       Pre-commit hooks setup
```

---

### Q6: Bakebook Property Requirements

**Decision: Intersection types from `ty`**

Use `Intersection` for type checking to ensure combined types have all required properties.

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ty_extensions import Intersection

    type PythonSpaceBakebook = Intersection[Bakebook, PythonSpaceRecipe]

def takes_python_bakebook(bb: PythonSpaceBakebook) -> None:
    bb.bake_lint()  # Type checker knows this exists
    bb.bake_test()  # And this
```

---

### Q7: Precomposed Bakebook Inheritance Order

**Decision: Bakebook last (top parent), recipes before**

```python
class PythonSpaceBakebook(PythonSpaceRecipe, Bakebook):
    pass
```

Bakebook is the rightmost (top parent). Recipes come before Bakebook so their methods take precedence. User can override in their own class.

---

### Q8: Naming Convention (FINAL)

**Decision: Food/kitchen theme with Recipe**

| Concept        | Naming Pattern             | Examples                               |
| -------------- | -------------------------- | -------------------------------------- |
| ABC            | `[Purpose]BaseRecipe`      | `SpaceBaseRecipe`, `ToolBaseRecipe`    |
| Implementation | `[Scope][Purpose]Recipe`   | `PythonSpaceRecipe`, `PreCommitRecipe` |
| Precomposed    | `[Scope][Purpose]Bakebook` | `PythonSpaceBakebook`                  |

**Rationale:**

- Fits "Bakebook" theme (cookbook contains recipes)
- Analogous to Justfile (recipes are tasks)
- `Base` prefix follows Pydantic/Python stdlib convention (`BaseModel`, `BaseException`)

```python
# ABC
class SpaceBaseRecipe:
    @abstractmethod
    def bake_lint(self): ...

# Implementation
class PythonSpaceRecipe(SpaceBaseRecipe):
    def bake_lint(self): ...  # ruff

# Precomposed
class PythonSpaceBakebook(PythonSpaceRecipe, Bakebook):
    pass
```

---

## File Structure

```
src/bakelib/
├── __init__.py
├── registry.py       # RecipeRegistry for discovery (later)
└── space/
    ├── __init__.py
    ├── base.py          # SpaceBaseRecipe ABC
    ├── python.py        # PythonSpaceRecipe (includes uv)
    ├── rust.py          # RustSpaceRecipe
    ├── javascript.py    # JavaScriptSpaceRecipe
    └── tools/
        ├── __init__.py
        ├── precommit.py     # PreCommitRecipe (space tool)
        └── docker.py        # DockerRecipe (space tool)
```

**Notes:**

- `python.py` includes uv functionality (opinionated choice)
- `space/tools/` contains tools that extend space recipes
- No pre-composed bundles - users compose recipes themselves

---

## Next Steps

1. [x] Resolve naming convention
2. [ ] Implement `RecipeRegistry`
3. [ ] Implement `SpaceBaseRecipe` ABC
4. [ ] Implement `PythonSpaceRecipe` as proof of concept
5. [ ] Implement `__requires__` validation
6. [ ] Test composition with multiple recipes
