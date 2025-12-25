# PROJECT_KNOWLEDGE.md

**Architecture overview and integration points for bakefile**

## Project Overview

**bakefile** is a Python-based task runner (Make/Justfile alternative) that uses OOP for task/recipe reusability.

**Key design goal:** Unlike Makefiles where tasks are not reusable, bakebook uses OOP patterns allowing tasks and variables to be composed, inherited, and reused.

## Core Concepts

| Term            | Purpose                                                           |
| --------------- | ----------------------------------------------------------------- |
| **bakefile.py** | User's task definition file (like Makefile, but Python)           |
| **bakebook**    | OOP container holding commands + variables (reusable, composable) |
| **bake**        | CLI that loads bakefile.py and executes bakebook commands         |
| **bakefile**    | Management CLI for bakefile projects (init, lint, docs)           |

## Architecture

```
┌─────────────────────────────────────────────┐
│           User's Repository                 │
│  bakefile.py  (like Makefile, but Python)   │
│                                             │
│  bakebook = Bakebook(                       │
│      commands=typer.Typer(),  # task defs   │
│      variables=BaseModel(),     # config     │
│  )                                          │
└─────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│              bake CLI                       │
│  1. Load bakefile.py from user repo         │
│  2. Retrieve bakebook object                │
│  3. Execute commands via typer app          │
└─────────────────────────────────────────────┘
```

## Bakebook Evolution

The `bakebook` object is evolving in phases:

| Phase        | bakebook Type    | Description                                    |
| ------------ | ---------------- | ---------------------------------------------- |
| Current (v0) | `str`            | Temporary placeholder, just echoes a string    |
| Next (v1)    | `typer.Typer`    | Commands only - enables subcommand support     |
| Future (v2)  | `Bakebook` class | Full OOP: commands + variables for reusability |

## Component Interactions

```
User runs: bake -C /path/to/project build --prod

bake CLI:
  1. resolve_bakebook()
     - change_directory() if -C specified
     - validate_file_name()
     - resolve_file_path()
     - load_module() - import bakefile.py
     - get_bakebook() - retrieve bakebook object
     - validate_bakebook() - ensure typer.Typer

  2. Execute bakebook(args=["build", "--prod"])
     - typer.Typer runs the build command
```

## Data Flow

```
bake command → resolve_bakebook() → typer.Typer → user's task execution
                │
                ├── file resolution
                ├── module loading
                └── type validation
```

## Technology Stack Decisions

| Technology   | Purpose                                              |
| ------------ | ---------------------------------------------------- |
| **Typer**    | CLI framework (used by both bake and user bakebooks) |
| **Pydantic** | Validation and settings (future: bakebook variables) |
| **UV**       | Fast Python package management                       |
| **pytest**   | Testing                                              |
| **ty**       | Linting                                              |

## File Organization

```
src/bakefile/
├── cli/
│   ├── bake/           # bake CLI (runs user tasks)
│   │   ├── main.py             # Entry point
│   │   └── resolve_bakebook.py # Load + validate bakebook
│   └── bakefile.py     # bakefile management CLI
examples/
└── simple/
    └── bakefile.py     # User-facing example
```
