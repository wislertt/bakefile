# README Documentation - Context

**Last Updated:** 2025-02-03

---

## SESSION PROGRESS

### ✅ COMPLETED

- Dev docs structure created (plan, context, tasks files)
- Codebase exploration completed for all API details

### 🟡 IN PROGRESS

- Awaiting user approval to proceed with README writing

### ⏳ PENDING

- Write README.md content
- User review and feedback
- Final revisions

---

## Key Decisions Made

### README Structure Agreement

User approved the revised structure with these key points:

1. **PEP 723 in Core Concepts** - Not a separate section
2. **bakelib positioning** - Optional, opinionated, built on top of bake (not core)
3. **No Advanced Features section** - Distribute content into bake/bakefile/bakelib sections
4. **No separate Examples section** - Include examples within relevant sections
5. **Bakebook API under Usage** - Not a separate top-level section

### Final Section Structure

```
README Structure:
├── Overview
├── Installation
├── Quick Start
├── Core Concepts
│   ├── Bakebook
│   ├── Commands & Context
│   ├── PEP 723 Support
│   └── Spaces (bakelib)
└── Usage
    ├── Bakebook API
    ├── bake CLI (Running Tasks)
    ├── bakefile CLI (Project Management)
    └── bakelib (Optional Spaces)
```

---

## Key Files

### `/README.md` (Target)

- Current: Only badges + "under active development" notice
- Goal: Complete documentation as single source of truth

### `/bakefile.py` (Example)

- Reference example bakefile
- May be used in Quick Start section

### `/src/bake/` (Main Package)

- **bakebook/** - Bakebook class and @command decorator
- **cli.py** - `bake` CLI implementation
- **context.py** - Context API with run(), run_script()
- **console.py** - Rich console output

### `/src/bakefile/` (Project Manager CLI)

- **cli.py** - `bakefile` CLI entry point
- Commands: init, lint, uv, add-inline, find-python, export

### `/src/bake/bakelib/` (Optional Spaces)

- **space/base.py** - BaseSpace (common tasks)
- **space/python.py** - PythonSpace (Python-specific)
- **space/python_lib.py** - PythonLibSpace (publishing)
- Position: Optional, opinionated helpers

### `/@examples/` (Usage Patterns)

- Simple bakefile example
- Python package example
- Reference for code samples

---

## Technical Constraints

### Documentation Style

- Clear, concise language
- Code examples for all major features
- No emojis unless user requests
- Markdown format with GitHub-compatible syntax

### Content Requirements

- README as single source of truth (aside from code comments)
- Position bakelib as optional, not required
- Include PEP 723 in Core Concepts, not separate
- Distribute examples throughout relevant sections

---

## API Reference Summary

### Bakebook Class

```python
from bake import Bakebook, command, Context

class MyBakebook(Bakebook):
    @command(help="Help text")
    def my_command(self, ctx: Context) -> None:
        ctx.run("echo hello")
```

### Context API

- `ctx.run()` - Execute commands
- `ctx.run_script()` - Execute multi-line scripts
- `ctx.dry_run` - Dry run property
- `ctx.verbosity` - Verbosity level (0-2)
- `ctx.override_dry_run()` - Context manager

### bake CLI Options

- `-C, --chdir` - Change directory
- `-f, --file-name` - Custom bakefile name
- `-b, --book-name` - Bakebook object name
- `-c, --chain` - Chain multiple commands
- `-v, --verbose` - Increase verbosity
- `-n, --dry-run` - Dry run mode

### bakefile CLI Commands

- `init` - Create new bakefile (--inline, --force)
- `lint` - Lint code (--only-bakefile)
- `uv` - Dependency management (sync, lock, add, pip)
- `add-inline` - Add PEP 723 metadata
- `find-python` - Find Python environment
- `export` - Export variables

---

## Quick Resume

To continue writing the README:

1. Read `/Users/wisl/Desktop/vault/personal-repo/bakefile/.dev/active/01-readme-documentation/plan.md` for the full plan
2. Read `/Users/wisl/Desktop/vault/personal-repo/bakefile/.dev/active/01-readme-documentation/tasks.md` for task checklist
3. Start with Phase 1 tasks in the task list
4. Write sections to `/README.md`

---

## Dependencies

### Blocked By

- None (awaiting user approval)

### Blocking

- None

---

## Notes

- Keep existing badges at top of README
- Use the exact section structure agreed upon with user
- bakelib must be clearly positioned as optional
- Include code examples liberally
- Reference @examples/ for sample code patterns
