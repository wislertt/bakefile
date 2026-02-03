# README Documentation - Implementation Plan

## Executive Summary

Create comprehensive README.md as the single source of truth for bakefile documentation (aside from code comments). The README will cover all three components: `bake` (task runner), `bakefile` (project manager), and `bakelib` (optional opinionated spaces).

**Last Updated:** 2025-02-03

---

## Current State Analysis

### Existing README

- **Location:** `/README.md`
- **Current Content:** Only badges and "under active development" notice
- **Status:** Incomplete, needs full documentation

### Project Understanding

Based on codebase exploration, bakefile is:

1. **OOP Task Runner** - Alternative to Make/Justfile with reusable tasks via inheritance
2. **Language Agnostic** - Uses Python but can manage any project type
3. **Two CLIs:**
    - `bake` - Runs tasks from bakefile.py
    - `bakefile` - Manages bakefile projects
4. **Modern Tech Stack** - Typer, Pydantic, UV, Rich, pytest

### Documentation Sources

- Code comments in source files
- `@examples/` directory for usage patterns
- `.claude/CLAUDE.md` for project guidance
- Test files for behavioral documentation

---

## Proposed Future State

A comprehensive README.md with the following structure:

```markdown
# bakefile

[Badges]

## Overview

- What is bakefile? (2-3 sentences)
- Why use it? (OOP reusability vs Make/Justfile)
- Language-agnostic but Python-powered

## Table of Contents

## Installation

- pip/uv install
- PEP 723 standalone option

## Quick Start

- Minimal hello world example
- Creating your first bakefile
- Running your first task

## Core Concepts

- Bakebook (OOP container for tasks)
- Commands & Context (@command decorator, ctx.run())
- PEP 723 Support (inline metadata)
- Spaces (bakelib - optional opinionated helpers)

## Usage

### Bakebook API

- Creating a Bakebook
- Defining commands
- Command parameters
- Context API reference
- Variables/settings (Pydantic)

### `bake` CLI - Running Tasks

- Basic execution
- Dry-run mode
- Verbosity levels
- Chaining commands
- Custom bakefile names
- Directory changes

### `bakefile` CLI - Project Management

- init (create new bakefile)
- lint (ruff, ty)
- uv (dependency management)
- add-inline (PEP 723 metadata)

### `bakelib` - Optional Spaces

- What is bakelib? (opinionated, optional)
- BaseSpace example (common tasks)
- PythonSpace example (Python tasks)
- Creating custom spaces

## Development

- Setting up dev environment
- Running tests (unit vs integration)
- Code quality (lint, format)

## Contributing

- How to contribute
- Code standards

## License
```

---

## Implementation Phases

### Phase 1: Foundation (15 min)

Write these sections first to establish the README structure:

- [ ] **Header & Badges** - Keep existing badges
- [ ] **Overview** - Clear 2-3 sentence summary + "Why bakefile?"
- [ ] **Table of Contents** - Auto-generated or manual links
- [ ] **Installation** - pip/uv instructions + PEP 723 note

**Acceptance:** README structure is established, reader understands what bakefile is and how to install it.

---

### Phase 2: Quick Start & Core Concepts (20 min)

These sections get users from zero to first running task:

- [ ] **Quick Start**
    - Minimal hello world example
    - Creating bakefile.py
    - Running with `bake hello`

- [ ] **Core Concepts**
    - Bakebook explanation
    - Commands & Context
    - PEP 723 Support
    - Spaces (bakelib positioning)

**Acceptance:** New user can create and run their first bakefile command after reading these sections.

---

### Phase 3: Usage - Bakebook API & bake CLI (25 min)

The core documentation for the task runner:

- [ ] **Bakebook API**
    - Creating a Bakebook (class-based)
    - @command decorator parameters
    - Context API (run, run_script, dry_run, verbosity)
    - Variables/settings (Pydantic integration)

- [ ] **`bake` CLI**
    - All options (--chdir, --file-name, --chain, --verbose, --dry-run)
    - Examples for each option
    - Common usage patterns

**Acceptance:** User understands how to define bakebooks and run tasks with all CLI options.

---

### Phase 4: Usage - bakefile CLI & bakelib (20 min)

Documentation for project management and optional spaces:

- [ ] **`bakefile` CLI**
    - init (--force, --inline)
    - lint (--only-bakefile, ruff options, ty option)
    - uv (sync, lock, add, pip)
    - add-inline
    - find-python
    - export

- [ ] **`bakelib` - Optional Spaces**
    - What is bakelib? (opinionated, built on top of bake)
    - BaseSpace example
    - PythonSpace example
    - Creating custom spaces
    - Link to bakelib source for details

**Acceptance:** User understands bakefile management commands and knows bakelib is optional.

---

### Phase 5: Development & Contributing (10 min)

Finish the README with contributor documentation:

- [ ] **Development**
    - Setting up dev environment
    - Running tests (bake test, bake test-integration, bake test-all)
    - Code quality (bake lint)

- [ ] **Contributing**
    - How to contribute
    - Code standards reference
    - Link to CLAUDE.md

- [ ] **License** - Add license section

**Acceptance:** README is complete and contributors know how to participate.

---

## Detailed Tasks with Acceptance Criteria

### Task 1.1: Write Header & Overview (S)

- [x] Keep existing badges
- [ ] Write 2-3 sentence overview
- [ ] Write "Why bakefile?" section comparing to Make/Justfile

**Acceptance:** Reader immediately understands what bakefile is and why they might use it.

---

### Task 1.2: Write Installation (S)

- [ ] pip install instructions
- [ ] uv add instructions
- [ ] PEP 723 standalone script option

**Acceptance:** User can install bakefile after reading this section.

---

### Task 2.1: Write Quick Start (M)

- [ ] Show minimal bakefile.py
- [ ] Show how to run it
- [ ] Expected output

**Acceptance:** User can copy-paste code and have a working bakefile.

---

### Task 2.2: Write Core Concepts (M)

- [ ] Explain Bakebook (OOP container)
- [ ] Explain @command decorator
- [ ] Explain Context object
- [ ] Explain PEP 723 inline metadata
- [ ] Explain Spaces (position bakelib as optional)

**Acceptance:** User understands the mental model of bakefile.

---

### Task 3.1: Write Bakebook API (L)

- [ ] Creating a Bakebook class
- [ ] @command decorator parameters table
- [ ] Context API methods (run, run_script, properties)
- [ ] Pydantic variables/settings
- [ ] Code examples for each

**Acceptance:** User can define bakebooks with all available features.

---

### Task 3.2: Write bake CLI docs (M)

- [ ] Document all CLI options
- [ ] Provide examples for each option
- [ ] Show common patterns (dry-run, chaining, verbosity)

**Acceptance:** User can use all bake CLI features effectively.

---

### Task 4.1: Write bakefile CLI docs (M)

- [ ] Document init command
- [ ] Document lint command
- [ ] Document uv subcommands
- [ ] Document add-inline, find-python, export

**Acceptance:** User can manage bakefile projects effectively.

---

### Task 4.2: Write bakelib section (M)

- [ ] Position as optional/opinionated
- [ ] Show BaseSpace example
- [ ] Show PythonSpace example
- [ ] Show custom space creation
- [ ] Link to source for full details

**Acceptance:** User understands bakelib is optional and how to use it if desired.

---

### Task 5.1: Write Development section (S)

- [ ] Dev environment setup
- [ ] Test commands (unit, integration, all)
- [ ] Code quality commands

**Acceptance:** Contributor can run tests and lint.

---

### Task 5.2: Write Contributing & License (S)

- [ ] Contributing guidelines
- [ ] Link to CLAUDE.md
- [ ] License section

**Acceptance:** README is complete.

---

## Risk Assessment and Mitigation

| Risk                        | Impact | Likelihood | Mitigation                                                |
| --------------------------- | ------ | ---------- | --------------------------------------------------------- |
| README becomes too long     | Medium | Medium     | Use collapsible sections if needed, keep examples concise |
| API changes invalidate docs | High   | Low        | Focus on stable APIs, version docs if needed              |
| Missing edge cases          | Low    | Medium     | Review test files for behavioral documentation            |
| bakelib positioning unclear | Low    | Medium     | Explicitly state it's optional in multiple places         |

---

## Success Metrics

1. **Completeness:** All agreed sections are written
2. **Clarity:** New user can go from zero to running a task
3. **Accuracy:** All documented features work as described
4. **Coverage:** All three CLIs (bake, bakefile, bakelib) are documented
5. **Positioning:** bakelib is clearly positioned as optional

---

## Required Resources and Dependencies

### Resources

- Time: ~90 minutes total
- User review and feedback

### Dependencies

- None (documentation task)

### Reference Files

- `/README.md` - Target file
- `/bakefile.py` - Example bakefile
- `/src/bake/` - Main package source
- `/src/bakefile/` - bakefile CLI source
- `/src/bake/bakelib/` - Spaces source
- `/@examples/` - Usage examples
- `/.claude/CLAUDE.md` - Project guidance

---

## Timeline Estimates

| Phase                               | Tasks    | Estimated Time |
| ----------------------------------- | -------- | -------------- |
| Phase 1: Foundation                 | 1.1, 1.2 | 15 min         |
| Phase 2: Quick Start & Concepts     | 2.1, 2.2 | 20 min         |
| Phase 3: Bakebook API & bake CLI    | 3.1, 3.2 | 25 min         |
| Phase 4: bakefile CLI & bakelib     | 4.1, 4.2 | 20 min         |
| Phase 5: Development & Contributing | 5.1, 5.2 | 10 min         |
| **Total**                           |          | **~90 min**    |

---

## Notes

- Write in clear, concise language
- Use code examples liberally
- Keep bakelib positioning clear (optional, opinionated)
- Reference existing badges and project structure
- Consider collapsible details if README gets long
