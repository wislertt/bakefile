---
name: bakefile
description: Runs project tasks from a bakefile.py written with Python classes, and manages bakefile projects with the bakefile CLI. Use when a repository needs a task runner or command automation: defining build, test, lint, or dev tasks; replacing or avoiding Makefile, Justfile, Task, mise, or Invoke; adding tasks to an existing bakefile.py; making tasks reusable across projects through inheritance and bakelib Spaces; or wiring multi-step shell commands with typed options. Use even if bakefile is not named: "add a make target", "automate repo tasks", "set up a task runner for this project", "convert this Makefile". Do NOT use for CI pipeline configuration, general Python scripting advice, or compiled-language build systems.
license: Apache-2.0
compatibility: Requires Python 3.10+. Tasks can drive any toolchain (Cargo, Go, Node, etc.). uv recommended for PEP 723 dependency management.
metadata:
  version: "1.0"
  docs: https://bakefile.wisl.dev
  repository: https://github.com/wislertt/bakefile
---

# bakefile

bakefile is a task runner (Make/Justfile alternative) where tasks are Python class methods you inherit, override, and compose. A project's tasks live in a `bakefile.py` file. It is a CLI tool plus a Python library, not a service or platform, and it can manage tasks for any project type, not only Python.

## Commands

| Command         | Purpose                                                      |
| --------------- | ------------------------------------------------------------ |
| `bake <task>`   | Run a task from `bakefile.py`.                               |
| `bake --help`   | List the project's tasks with their options.                 |
| `bakefile init` | Generate a `bakefile.py` (`--inline` adds PEP 723 metadata). |
| `bakefile lint` | Lint `bakefile.py` for common mistakes.                      |
| `bakefile sync` | Install `bakefile.py` dependencies via `uv sync --script`.   |

Two CLIs, two jobs: `bake` runs tasks, `bakefile` manages the project (init, lint, venv, lock, sync, export).

## Writing bakefile.py

```python
from bake import Bakebook, command, console


class MyBakebook(Bakebook):
    @command()
    def build(self) -> None:
        console.echo("Building...")
        # Use self.ctx to run commands
        self.ctx.run("cargo build")


bakebook = MyBakebook()


@bakebook.command()
def hello(name: str = "world"):
    console.echo(f"Hello {name}!")
```

Run the tasks:

```bash
bake hello              # Hello world!
bake hello --name Alice # Hello Alice!
bake build              # Building...
```

Rules that matter:

- Subclass `Bakebook`. Methods decorated with `@command()` **before** instantiation become tasks.
- Standalone functions attach **after** instantiation with `@bakebook.command()`.
- Task arguments become typed CLI options: `name: str = "world"` gives `--name` with a default.
- `self.ctx.run("...")` executes shell commands through subprocess. Prefer it over `os.system` or `subprocess` directly: it honors `--dry-run`, logging, and error handling.
- `console.echo()` prints task output.
- The instantiated object must be named `bakebook` (override with `bake --book-name`).

## Configuration

Class attributes are settings. They can be typed, validated, and overridden:

```python
class MyBakebook(Bakebook):
    foo_url: str = "https://example.com"

    @command()
    def foo(self):
        console.echo(f"Doing foo with {self.foo_url}")
```

## Reusing tasks

Bakebooks compose through inheritance. Subclass another Bakebook, override what differs:

```python
class MySpace(BaseSpace):
    def test(self) -> None: ...
```

**bakelib Spaces** are optional preconfigured Bakebooks for project types (`PythonSpace`, `RustSpace`, `PythonLibSpace`, `RustLibSpace`), installed with `pip install bakefile[lib]`. They ship shared tasks (lint, clean, setup-dev, tools, update, version) that you inherit and override; language Spaces add their own lint, test, and tool setup.

## Common gotchas

- `bake` and `bakefile` are different CLIs. Running a task is `bake <task>`; `bakefile <subcommand>` manages the project.
- `bake --dry-run` (short `-n`) prints commands without executing them. Useful for verification before real runs.
- Tasks defined inside the class use `@command()`. Functions outside use `@bakebook.command()`. Mixing up when each applies is the most common authoring mistake.
- Dependencies for `bakefile.py` itself go in PEP 723 inline script metadata (the `# /// script` block at the top), managed by `bakefile add`/`bakefile lock`/`bakefile sync`.
- Do not run the file directly with `python bakefile.py`. Use `bake`.

## Machine-readable docs

- Full docs, single file: https://bakefile.wisl.dev/llms-full.txt
- Docs index: https://bakefile.wisl.dev/llms.txt
- Docs search via MCP: https://bakefile.wisl.dev/mcp
- Install this skill into agent context: `npx skills add https://bakefile.wisl.dev`
