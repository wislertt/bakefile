# Bakelib Mixin System - Tasks

## Phase 1: Foundation

- [x] Resolve naming convention
- [ ] Create `src/bakelib/` package structure
- [ ] Implement `RecipeRegistry` class
    - [ ] `register()` decorator
    - [ ] `list_all()` method
- [ ] Implement `SpaceBaseRecipe` ABC

## Phase 2: Proof of Concept

- [ ] Implement `PythonSpaceRecipe`
    - [ ] `bake_lint` → ruff
    - [ ] `bake_test` → pytest
    - [ ] Register with `@register_recipe()`
- [ ] Implement `__requires__` validation
    - [ ] Metaclass or `__init_subclass__` hook
    - [ ] Clear error messages
- [ ] Add tests for PythonSpaceRecipe
- [ ] Update example bakefile to use recipe

## Phase 3: Tool Recipes

- [ ] Implement `PreCommitRecipe`
- [ ] Implement `UVRecipe`
- [ ] Test composition of multiple recipes
- [ ] Test `super()` for command composition

## Phase 4: Additional Languages

- [ ] Implement `RustSpaceRecipe`
- [ ] Implement `JavaScriptSpaceRecipe`

## Phase 5: Polish

- [ ] Implement `bake recipes` CLI command
- [ ] Documentation
- [ ] Integration tests
- [ ] Type checking with `Intersection`
