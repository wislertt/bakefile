# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
make test   # Run tests with coverage
make lint   # Run all linters and formatters
```

## Project

**bakefile** - Python-based build system (Make/Justfile alternative) using OOP for reusability.

- Tech: Typer, Pydantic, UV, pytest, ty
- `bake` CLI - runs commands from `bakefile.py`
- `bakefile` CLI - manages bakefile (init, lint, docs)

## Dev Docs

Active work uses `.dev/active/` with three-file structure:

- `plan.md` - Strategic plan
- `context.md` - Key decisions & files (update frequently!)
- `tasks.md` - Checklist format

**Naming:** `.dev/active/[xx-task-name]/` where `xx` is an incremental number (01, 02, ...) and `task-name` is a concise kebab-case name.

Use `/dev-docs` command to create these automatically.
