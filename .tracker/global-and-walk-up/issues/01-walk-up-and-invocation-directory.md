# 01: Walk-up and invocation directory

Status: resolved

Blocked by: None (can start immediately)

Spec: `.tracker/global-and-walk-up/spec.md`. Decision: `docs/adr/0005-one-bakefile-per-run-no-merging.md`.

**What to build:** Running `bake <cmd>` or a `bakefile` subcommand from any subfolder finds the nearest `bakefile.py` by walking up to the filesystem root, and runs commands in that file's directory. `-f` changes only the file name looked for. `-C` stays an exact directory: no walk-up, and a miss is an error. `bakefile init` never walks up. Commands can read the Invocation directory as `ctx.invocation_dir`.

Start with the prefactor: path resolution returns a result (chosen path, how it was found, what was searched) instead of a bare path, with no behaviour change. Ticket 02 adds the global steps to that result. Add the root-conftest autouse fixture that points `BAKE_CONFIG_DIR` and `XDG_CONFIG_HOME` at an empty temp directory, so no test can read a developer's real global directory or depend on files above its temp folder.

- [x] Prefactor lands with the full suite green and no behaviour change
- [x] Autouse fixture isolates every test (unit and integration) from the real global directory
- [x] `bake <cmd>` from a nested folder runs the nearest parent `bakefile.py`, in that file's directory
- [x] With nested `bakefile.py` files, the nearest one wins
- [x] `bake -f tools.py <cmd>` walks up looking for `tools.py`
- [x] `bake -C <dir>` looks only in `<dir>` and errors when the file is missing there
- [x] `bakefile` subcommands (lock, add, sync, lint, ...) resolve by walk-up the same way
- [x] `bakefile init` creates in the current directory (or `-C`) even when a parent has a `bakefile.py`
- [x] Chained commands (`bake a b c`) all run against the one resolved file
- [x] `bake --help` shows the path of the loaded `bakefile.py`
- [x] `bakefile` subcommands other than `init` print `Using: <absolute path>` to stderr before running (not for `--help`, not when no file is found, not again in a re-invoked child)
- [x] `ctx.invocation_dir` is the directory `bake` was called from, captured before the directory change, and stays correct after re-invocation under the `bakefile.py`'s Python
- [x] Tests go through `run_cli` with a temp tree and an identity command that prints book identity, working directory and `ctx.invocation_dir`
- [x] `GLOSSARY.md` terms used: Invocation directory

## Comments

- Implemented on `feat/walk-up-and-invocation-directory`, PR wislertt/bakefile#161 into `chore/docs-site`.
- The prefactor (`BakefileResolution`) landed in the same commit as walk-up, not as its own green step.
- Besides the global-directory fixture, a session guard stops the test run when a `bakefile.py` sits above pytest's temp root.
