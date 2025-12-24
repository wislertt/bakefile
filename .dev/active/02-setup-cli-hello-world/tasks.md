# Setup CLI Hello World - Task Checklist

**Last Updated: 2025-12-24**

---

## Phase 1: Add CLI Dependency ✅

- [x] Add typer to dependencies in pyproject.toml
    - Acceptance: `typer>=0.0.1` added to `dependencies` list
    - Verify: `uv sync` completes successfully

---

## Phase 2: Create CLI Module Structure ✅

- [x] Create cli directory and **init**.py
    - Acceptance: `src/bakefile/cli/__init__.py` exists

---

## Phase 3: Implement bake CLI ⏳

- [ ] Create src/bakefile/cli/bake.py
    - Acceptance: File created with typer app that prints "hello world"
- [ ] Add bake entry point to pyproject.toml
    - Acceptance: `bake = "bakefile.cli.bake:app"` in `[project.scripts]`

---

## Phase 4: Implement bakefile CLI ⏳

- [ ] Create src/bakefile/cli/bakefile.py
    - Acceptance: File created with typer app that prints "hello world"
- [ ] Add bakefile entry point to pyproject.toml
    - Acceptance: `bakefile = "bakefile.cli.bakefile:app"` in `[project.scripts]`

---

## Phase 5: Add CLI Tests ⏳

- [ ] Create tests/cli/ directory structure
    - Acceptance: `tests/cli/__init__.py` exists
- [ ] Create tests/cli/test_bake.py
    - Acceptance: Test file for `bake` CLI that verifies "hello world" output
- [ ] Create tests/cli/test_bakefile.py
    - Acceptance: Test file for `bakefile` CLI that verifies "hello world" output

## Phase 6: Test Both CLIs ⏳

- [ ] Install package with uv sync
    - Acceptance: No errors during sync
- [ ] Test bake command manually
    - Acceptance: Running `bake` outputs "hello world"
- [ ] Test bakefile command manually
    - Acceptance: Running `bakefile` outputs "hello world"
- [ ] Run make lint
    - Acceptance: All linters pass
- [ ] Run make test
    - Acceptance: All tests pass (including new CLI tests)

---

## Progress Summary

| Phase                           | Status         | Tasks    |
| ------------------------------- | -------------- | -------- |
| Phase 1: Add CLI Dependency     | ✅ Complete    | 1/1      |
| Phase 2: Create CLI Structure   | ✅ Complete    | 1/1      |
| Phase 3: Implement bake CLI     | ⏳ Not Started | 0/2      |
| Phase 4: Implement bakefile CLI | ⏳ Not Started | 0/2      |
| Phase 5: Add CLI Tests          | ⏳ Not Started | 0/3      |
| Phase 6: Test Both CLIs         | ⏳ Not Started | 0/5      |
| **TOTAL**                       | **🟡 14%**     | **2/14** |

---

## Quick Resume

1. Read `context.md` for key files and decisions
2. Start with Phase 1: Add typer dependency
3. Work through each phase sequentially
4. Update this file as tasks are completed
