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

Active work uses `dev/active/` with three-file structure:

- `[task]-plan.md` - Strategic plan
- `[task]-context.md` - Key decisions & files (update frequently!)
- `[task]-tasks.md` - Checklist format

Use `/dev-docs` command to create these automatically.
