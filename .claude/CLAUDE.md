# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
make test   # Run tests with coverage
make lint   # Run all linters and formatters
```

## Project

Python package template using UV for package management. Currently a minimal hello world.

## Planning

Use `.claude/plan/` for task plans:

- File format: `xx-task-name.md`
- `xx` = incremental number (01, 02, 03, ...)
- `task-name` = kebab-case description

## Reference Docs

Use `.claude/ref/` for detailed reference docs:

- Store content that's too long for CLAUDE.md
- Reference the path to `.md` files in ref/ instead of duplicating content
