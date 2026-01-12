# Bakelib Mixin System - Tasks

**Key Insight:** No separate "Recipe" or "Mixin" concept needed. Everything inherits from `Bakebook` directly. Multiple inheritance provides composition.

## Phase 1: Foundation

- [x] Resolve naming convention
- [ ] Create `src/bakelib/` package structure
- [ ] Implement base Bakebook classes for common patterns

## Phase 2: Proof of Concept

- [ ] Implement `PythonSpace` (Bakebook with Python dev commands)
    - [ ] `lint` → ruff
    - [ ] `test` → pytest
    - [ ] `install` → uv install
    - [ ] `lock` → uv lock
- [ ] Create `PythonProject` precomposed class
- [ ] Add tests for PythonSpace
- [ ] Update example bakefile to use mixin classes
- [ ] Test composition with multiple Bakebook base classes

## Phase 3: Multiple Inheritance Patterns

- [ ] Document MRO behavior for Bakebook composition
- [ ] Test field name conflicts (leftmost parent wins)
- [ ] Test command name conflicts (leftmost parent wins)
- [ ] Test deep inheritance chains
- [ ] Test method override with/without @command decorator
- [ ] Test diamond inheritance pattern

## Phase 4: Tool Bakebooks

- [ ] Implement `PreCommit` (in space/tools/)
- [ ] Implement `Docker` (in space/tools/)
- [ ] Test `super()` for command composition

## Phase 5: Additional Languages

- [ ] Implement `RustSpace`
- [ ] Implement `JavaScriptSpace`

## Phase 6: Polish

- [ ] Implement `bake recipes` CLI command (list available bakelib classes)
- [ ] Documentation
- [ ] Integration tests
- [ ] Type checking
