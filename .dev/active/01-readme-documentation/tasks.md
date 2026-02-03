# README Documentation - Task Checklist

**Last Updated:** 2025-02-03

## IMPORTANT: Proceed Exactly as Requested

**When user specifies a task number (e.g., "1.1" or "Task 1.1"), ONLY complete that specific task.** Do not proceed to other tasks unless explicitly asked. This prevents over-delivering and allows for review/feedback between tasks.

Examples:

- User says "proceed 1.1" → Only do Task 1.1
- User says "do 1.2 and 1.3" → Only do Tasks 1.2 and 1.3
- User says "continue" → Ask which task to proceed with

---

## Phase 1: Foundation ✅ COMPLETE

- [x] Task 1.1: Write Header & Overview
    - Keep existing badges
    - Write 2-3 sentence overview
    - Write "Why bakefile?" section
    - **Acceptance:** Reader understands what bakefile is and why to use it

- [x] Task 1.2: Write Installation
    - pip install instructions
    - uv add instructions
    - uv tool install option
    - **Acceptance:** User can install bakefile

---

## Phase 2: Quick Start & Core Concepts ✅ COMPLETE

- [x] Task 2.1: Write Quick Start
    - Show minimal bakefile.py
    - Show how to run it
    - Show expected output
    - Show bakefile init options
    - **Acceptance:** User can copy-paste and run

- [x] Task 2.2: Write Core Concepts
    - Two CLIs (bake, bakefile)
    - Explain Bakebook (inherit, Pydantic, @command, ctx.run)
    - Explain PEP 723 inline metadata
    - **Acceptance:** User understands the mental model

---

## Phase 3: Usage - Bakebook API & bake CLI ✅ COMPLETE

- [x] Task 3.1: Write Bakebook API
    - Creating a Bakebook class
    - @command decorator parameters
    - Context API (run, run_script, properties)
    - Pydantic variables/settings
    - Code examples
    - **Acceptance:** User can define bakebooks with all features

- [x] Task 3.2: Write bake CLI docs
    - Document all CLI options
    - Provide examples for each
    - Show common patterns
    - **Acceptance:** User can use all bake CLI features

---

## Phase 4: Usage - bakefile CLI & bakelib ⏳ NOT STARTED

- [ ] Task 4.1: Write bakefile CLI docs
    - Document init command
    - Document lint command
    - Document uv subcommands
    - Document add-inline, find-python, export
    - **Acceptance:** User can manage bakefile projects

- [ ] Task 4.2: Write bakelib section
    - Position as optional/opinionated
    - Show BaseSpace example
    - Show PythonSpace example
    - Show custom space creation
    - Link to source for details
    - **Acceptance:** User understands bakelib is optional

---

## Phase 5: Development & Contributing ⏳ NOT STARTED

- [ ] Task 5.1: Write Development section
    - Dev environment setup
    - Test commands (unit, integration, all)
    - Code quality commands
    - **Acceptance:** Contributor can run tests and lint

- [ ] Task 5.2: Write Contributing & License
    - Contributing guidelines
    - Link to CLAUDE.md
    - License section
    - **Acceptance:** README is complete

---

## Overall Progress

| Phase                               | Status             | Tasks    |
| ----------------------------------- | ------------------ | -------- |
| Phase 1: Foundation                 | ✅ Complete        | 2/2      |
| Phase 2: Quick Start & Concepts     | ✅ Complete        | 2/2      |
| Phase 3: Bakebook API & bake CLI    | ✅ Complete        | 2/2      |
| Phase 4: bakefile CLI & bakelib     | ⏳ Not Started     | 0/2      |
| Phase 5: Development & Contributing | ⏳ Not Started     | 0/2      |
| **Total**                           | **🟡 In Progress** | **6/10** |

---

## Quick Resume

**Current Status:** Phase 3 (Usage - Bakebook API & bake CLI) is complete. README.md currently contains:

- All existing badges
- Overview paragraph
- "Why bakefile?" section (3 bullets)
- Installation section (pip, uv add, uv tool install)
- Quick Start section (bakefile.py example, bakefile init tip, run commands)
- Core Concepts section (Two CLIs, Bakebook with bullets + example, PEP 723)
- Usage section - Bakebook API (Creating, @command patterns, Context API, Pydantic settings)
- Usage section - bake CLI (Basic execution, dry-run, verbosity, chaining, options)

**Next Step:** Awaiting user instruction to proceed with Phase 4 (bakefile CLI & bakelib) or other task.
