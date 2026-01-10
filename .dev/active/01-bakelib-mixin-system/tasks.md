# Bakelib Mixin System - Tasks

## Phase 1: Foundation

- [x] Resolve naming convention
- [ ] Create `src/bakelib/` package structure
- [ ] Implement `SpaceBaseRecipe` ABC

## Phase 2: Proof of Concept

- [ ] Implement `PythonSpaceRecipe`
    - [ ] `bake_lint` → ruff
    - [ ] `bake_test` → pytest
    - [ ] uv commands (install, lock, etc.)
- [ ] Create `PythonSpaceBakebook` precomposed class
- [ ] Add tests for PythonSpaceRecipe
- [ ] Update example bakefile to use recipe
- [ ] Test composition with multiple recipes

## Phase 3: Advanced Features

- [ ] Implement `__requires__` validation
    - [ ] Metaclass or `__init_subclass__` hook
    - [ ] Clear error messages
- [ ] Implement `RecipeRegistry` class
    - [ ] `register()` decorator
    - [ ] `list_all()` method

## Phase 4: Tool Recipes

- [ ] Implement `PreCommitRecipe` (in space/tools/)
- [ ] Implement `DockerRecipe` (in space/tools/)
- [ ] Test `super()` for command composition

## Phase 5: Additional Languages

- [ ] Implement `RustSpaceRecipe`
- [ ] Implement `JavaScriptSpaceRecipe`

## Phase 6: Polish

- [ ] Implement `bake recipes` CLI command
- [ ] Documentation
- [ ] Integration tests
- [ ] Type checking with `Intersection`
