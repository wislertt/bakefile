# Global `bakefile.py` and walk-up resolution

Status: ready-for-agent

## Problem Statement

`bake` only finds a `bakefile.py` in the current directory (or the one given with `-C`). Running `bake test` from a subfolder of a project fails, even though the project's `bakefile.py` is a few levels up. Commands that are not tied to any project, such as syncing dotfiles or personal utilities, have no home: the user has to `cd` into the repo holding them or type `bake -C <path>` every time. Other task runners (just, go-task, mise) handle both cases, so users coming from them expect it.

## Solution

`bake` and `bakefile` pick exactly one `bakefile.py` per run (ADR 0005):

1. With `-g`, the Global `bakefile.py`.
2. With `-C`, only that exact directory: no walk-up, no fallback.
3. Otherwise, the nearest `bakefile.py` found by walking up from the current directory to the filesystem root.
4. If none is found, the Global `bakefile.py`, when the user has created one.

`-f` only changes the file name, and every step above looks for that name. The global directory is `$BAKE_CONFIG_DIR`, else `$XDG_CONFIG_HOME/bake/`, else `~/.config/bake/`. A user can symlink a whole dotfiles repo there. Commands always run in the chosen `bakefile.py`'s directory, and the Invocation directory is available on the context for commands that need to act where the user called them from.

## User Stories

1. As a developer, I want to run `bake test` from any subfolder of my project, so that I don't have to `cd` to the project root first.
2. As a developer, I want walk-up to pick the nearest `bakefile.py`, so that a nested project with its own `bakefile.py` uses its own commands.
3. As a developer, I want commands found by walk-up to run in the `bakefile.py`'s directory, so that relative paths inside my commands behave the same as when I run from the root.
4. As a developer, I want `bake -C <dir>` to look only in `<dir>`, so that naming a directory never silently loads a different `bakefile.py`.
5. As a developer, I want `bake -C <dir>` to fail when `<dir>` has no `bakefile.py`, so that a typo in the path is caught.
6. As a developer, I want `bake -f tools.py` to walk up looking for `tools.py`, so that alternative file names get the same convenience as `bakefile.py`.
7. As a user with personal commands, I want a Global `bakefile.py` in `~/.config/bake/`, so that I can run those commands from any directory.
8. As a user, I want the global directory to honour `$XDG_CONFIG_HOME`, so that it follows my XDG layout like mise and just do.
9. As a user, I want to override the global directory with `BAKE_CONFIG_DIR`, so that I can point it anywhere, including in tests and CI.
10. As a dotfiles maintainer, I want to symlink my dotfiles repo to `~/.config/bake`, so that `bake -g` runs the commands kept in that repo.
11. As a dotfiles maintainer, I want global commands to run in the real (symlink-resolved) repo directory, so that the repo's relative paths and `bakefile.py.lock` work.
12. As a user, I want `bake -g <cmd>` to always use the Global `bakefile.py`, so that I can reach global commands from inside a project that has its own `bakefile.py`.
13. As a user, I want plain `bake <cmd>` to fall back to the Global `bakefile.py` when no `bakefile.py` is found walking up, so that global commands work without `-g` outside projects.
14. As a user without a Global `bakefile.py`, I want `bake` to behave exactly as it does today when nothing is found, so that the feature costs me nothing until I opt in.
15. As a user, I want `bake -f tools.py` to fall back to the global `tools.py`, so that `-f` means the same thing at every step.
16. As a dotfiles maintainer, I want `bake -g -f mac.py <cmd>`, so that I can keep several global Bakebooks in one repo.
17. As a user, I want `-g` together with `-C` to be a usage error, so that contradictory options are not silently resolved.
18. As a user, I want a missing command in the chosen Bakebook to be an error, so that `bake build` never runs a `build` from a different layer.
19. As a user, I want `bake --help` to show which `bakefile.py` was loaded, including when it came from the global fallback, so that I can tell why unexpected commands appear.
20. As a user, I want the global fallback to be silent on normal runs, so that a deliberate setup does not print noise every time.
21. As a user, I want the global fallback to show up in debug logs, so that `-vvv` explains which file was chosen.
22. As a user, I want the "not found" message to say it searched the start directory and its parents, so that I understand walk-up happened.
23. As a user, I want the "not found" message to always show the global path and whether it exists, so that I learn where a Global `bakefile.py` would go.
24. As a user running `bake -g` with no global directory, I want an error suggesting `bakefile -g init`, so that I know how to set it up.
25. As a user, I want `bakefile -g init` to create the global directory and a Global `bakefile.py`, so that setup is one command.
26. As a user, I want `bakefile init` to always create in the current directory (or `-C`), never in a parent or the global directory, so that init is predictable.
27. As a user, I want `bakefile lock/add/sync/lint` to resolve the file the same way as `bake`, so that I can manage a project's `bakefile.py` from a subfolder.
28. As a user, I want `bakefile -g lock` and `bakefile -g add <pkg>`, so that I can manage a Bakefile-level Global `bakefile.py` like mise's `use -g` edits the global config.
29. As a Bakebook author, I want `ctx.invocation_dir`, so that a global command like "clean caches here" can act on the directory I ran it from.
30. As a Bakebook author, I want `ctx.invocation_dir` to stay correct when `bake` re-runs itself under the `bakefile.py`'s Python, so that the value does not depend on environment detection.
31. As a user of a Bakefile-level Global `bakefile.py`, I want re-invocation under its isolated environment to load the same global file, so that `-g` and fallback work with inline metadata.
32. As a user of a Project-level `bakefile.py` found by walk-up, I want the project's environment to be detected from the `bakefile.py`'s directory, so that running from a subfolder uses the right `.venv`.
33. As a user, I want error hints that name the `bakefile.py` to use its resolved absolute path, so that copy-pasting a hint works from a subfolder or with `-g`.
34. As a user, I want chained commands (`bake a b c`) to resolve once and run all commands against the same Bakebook, so that walk-up and fallback behave the same in chains.
35. As a user, I want `-b <book-name>` to work with walk-up, `-g` and fallback, so that selecting a Bakebook object is independent of how the file was found.
36. As a user, I want `--dry-run` to work unchanged with `-g` and walk-up, so that I can preview global commands.
37. As a contributor, I want the test suite isolated from my real `~/.config/bake` and stray parent `bakefile.py` files, so that tests pass the same on every machine.
38. As a user upgrading, I want the changelog to mention that running from a subfolder now finds a parent `bakefile.py`, so that the behaviour change is not a surprise.

## Implementation Decisions

- **One `bakefile.py` per run** (ADR 0005): no merging of layers, no per-command fallback to another layer.
- **Resolution order**: `-g` → global; `-C` → exact directory only; else walk up from the current directory to the filesystem root; else the global directory if the file exists there. No ceiling paths.
- **`-f` scope**: changes the file name only. Walk-up, fallback and `-g` all use it. It still rejects path separators.
- **Global directory**: `BAKE_CONFIG_DIR` if set, else `$XDG_CONFIG_HOME/bake`, else `~/.config/bake`, on every platform (not macOS `~/Library`). Read through the existing settings object alongside the other `BAKE_` variables.
- **Global is opt-in**: nothing creates the global directory except `bakefile -g init`. `bake` never creates it.
- **`-g` / `--global`**: a new shared option on both CLIs, parsed into the `BakefileObject` like `-C`, `-f`, `-b`. `-g` with an explicit `-C` is a usage error.
- **Path resolution** lives in the existing bakefile path resolution module and returns both the chosen path and how it was found (walk-up, global fallback, explicit global, exact `-C`), plus the list of what was searched, so the not-found message and `--help` header can report it. Resolution happens once per process; chained commands reuse it.
- **Working directory**: unchanged rule, commands run in the chosen `bakefile.py`'s directory (resolved through symlinks).
- **Invocation directory**: captured before any `chdir`, stored on the `BakefileObject`, and exposed as `ctx.invocation_dir`. Re-invocation runs the child from the Invocation directory with the same argv, so it resolves identically even when `bakefile env` or `export` re-invoke after changing into the `bakefile.py`'s directory.
- **Not-found message** replaces `Searched in: <dir>` with the start directory "and parent directories" (or the exact `-C` directory) and a `Global:` line showing the global path and whether it exists. The line is always shown.
- **`bake -g` with no global file**: error that names the global path and suggests `bakefile -g init`.
- **Fallback visibility**: the `bake --help` output shows the loaded `bakefile.py` path as `Using: <absolute path>` and marks it as global when it is. A debug log line records which resolution step matched. `bake` prints no notice on normal runs. `bakefile` subcommands other than `init` print `Using: <absolute path>` to stderr before running, on success and failure alike, because they act on the file itself (lock, add, add-inline, lint) and walk-up may have picked a parent's file.
- **`bakefile` CLI**: all subcommands use the same resolution, except `init`, which always targets the current directory (or `-C`), and with `-g` the global directory, creating it if missing.
- **Hints with file paths** (for example the broken-environment hint after re-invocation) print the resolved absolute `bakefile.py` path instead of a bare `bakefile.py`.
- **Glossary**: uses **Global `bakefile.py`** and **Invocation directory** as defined in `GLOSSARY.md`.

## Testing Decisions

- Good tests drive the real CLI entry point with an argv and assert on stdout, stderr and exit code. They do not call the path resolution function directly and do not assert on internal state.
- **One seam**: the existing in-process `run_cli` helper, which runs `bake`/`bakefile` `main()` with a given argv. Prior art: the `bake` and `bakefile` `main` unit tests under `tests/unit/bake/cli/`.
- **New fixture**: a temp tree with `project/bakefile.py`, an empty `project/a/b/`, `project/tools.py`, `global/bakefile.py` and `global/tools.py`. `BAKE_CONFIG_DIR` points at `global/`, and the test changes into the start directory. Each test bakefile has an identity command that prints its book identity, `Path.cwd()` and `ctx.invocation_dir`.
- `run_cli` adds `-C` when given a directory, so existing tests keep exact-directory behaviour. New walk-up tests call it with no directory after changing into the start directory.
- **Cases**: walk-up from a nested directory; nearest wins with nested `bakefile.py`; `-C` exact and its miss; `-f` walk-up; fallback to global; `-f` fallback to global `-f` file; `-g` from inside a project; `-g -f`; `-g` with `-C` errors; missing command does not fall through; no global file gives today's behaviour; the not-found message contents with and without a global file; `bake -g` with no global directory suggests init; `bakefile init` ignores walk-up; `bakefile -g init` creates the directory; `XDG_CONFIG_HOME` used when `BAKE_CONFIG_DIR` is unset; symlinked global directory runs in the resolved directory; `ctx.invocation_dir` correct for walk-up and `-g`; chained commands.
- **Isolation**: an autouse fixture in the root test conftest sets `BAKE_CONFIG_DIR` and `XDG_CONFIG_HOME` to an empty temp directory for every test, unit and integration, so a developer's real global directory is never read.
- **One integration test** (prior art: the reinvocation tests under `tests/integration/fixtures/`): a Bakefile-level Global `bakefile.py` run via `-g` from an unrelated directory re-invokes under its own environment and reports the right file and Invocation directory.

## Out of Scope

- Mise-style merging of several `bakefile.py` layers, or running commands from more than one Bakebook in one run.
- Falling through to a parent or global `bakefile.py` when a command is missing (just's `fallback` setting).
- Ceiling paths to stop walk-up (`BAKE_CEILING_PATHS`). Can be added later.
- A system-wide layer such as `/etc/bake`.
- Any per-command opt-out of running in the `bakefile.py`'s directory (just's `[no-cd]`). `ctx.invocation_dir` covers the need.
- bake settings or config files in the global directory.

## Further Notes

- Measured walk-up cost is about 0.05 ms for 9 levels, against 1 to 3.7 s for `uv run bake --help`, so performance is not a concern.
- Walk-up crosses repository boundaries, for example from a git submodule without its own `bakefile.py` into the outer repo. Accepted with no ceiling.
- Suggested ticket order: test isolation fixture, global directory and `-g`, walk-up with `-f`, global fallback and not-found message, `ctx.invocation_dir`, then hint paths and changelog.
- Decision record: `docs/adr/0005-one-bakefile-per-run-no-merging.md`.
