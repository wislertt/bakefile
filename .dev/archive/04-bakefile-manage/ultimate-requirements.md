# Bakefile Python Environment Management

**Status:** PARTIALLY COMPLETED

## Goal

Enable `bakefile` to manage its own Python runtime and dependencies, independent of the host project's Python setup.

## Implementation Status

| Command       | Status         | See                                            |
| ------------- | -------------- | ---------------------------------------------- |
| `init`        | ✅ Complete    | `src/bake/cli/bakefile/init.py`                |
| `find-python` | ✅ Complete    | `.dev/archive/05-find-python/`                 |
| `add-inline`  | ✅ Complete    | `src/bake/cli/bakefile/add_inline.py`          |
| `pip`         | ⏳ Planned     | `.dev/active/08-bakefile-dependency-commands/` |
| `add`         | ⏳ Planned     | `.dev/active/08-bakefile-dependency-commands/` |
| `lock`        | ⏳ Planned     | `.dev/active/08-bakefile-dependency-commands/` |
| `sync`        | ⏳ Planned     | `.dev/active/08-bakefile-dependency-commands/` |
| `lint`        | ⏳ Not started | —                                              |
| `update`      | ⏳ Not started | —                                              |

## Requirements

### 1. Folder Structure

- ✅ Create `src/bake/manage/` for business logic (DONE)
- ✅ Keep CLI commands in `src/bake/cli/bakefile/` as thin wrappers (DONE)

### 2. New `bakefile` Subcommands

| Command       | Purpose                                                 |
| ------------- | ------------------------------------------------------- |
| `init`        | Create bakefile locally (exists)                        |
| `find-python` | Find Python exe for bakefile (project or file-isolated) |
| `add-inline`  | Add PEP 723 inline metadata to bakefile                 |
| `pip`         | Manage pip for that Python (wrapper around uv pip)      |
| `add`         | Add dependencies (like uv add)                          |
| `lock`        | Lock dependencies (like uv lock)                        |
| `sync`        | Sync dependencies (like uv sync)                        |
| `lint`        | Lint bakefile (ruff + mypy)                             |
| `update`      | Update lockfile (like uv lock --upgrade)                |

### 3. Python Detection Strategy

Use project-level Python if exists (`.venv`), otherwise use file-isolated Python (PEP 723).

Built on top of `uv` capabilities.

## Test Scenarios

1. Empty repo (any language)
2. Repo with invalid `pyproject.toml`
3. Repo with valid uv project
