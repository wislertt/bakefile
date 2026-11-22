# 03: User docs for walk-up and Global `bakefile.py`

Status: resolved

Blocked by: 02 (Global `bakefile.py`)

Spec: `.tracker/global-and-walk-up/spec.md`. Decision: `docs/adr/0005-one-bakefile-per-run-no-merging.md`.

**What to build:** A user reading the README or the docs site learns how `bake` picks a `bakefile.py`, how to set up a Global `bakefile.py`, and how to write commands that act on the Invocation directory. Users upgrading learn that running from a subfolder now finds a parent `bakefile.py`.

- [x] Resolution order documented: `-g`, `-C` exact, walk-up (with `-f`), then global fallback
- [x] Global directory location and override (`BAKE_CONFIG_DIR`, `XDG_CONFIG_HOME`), with the dotfiles symlink example and `bakefile -g init`
- [x] `-g` on both CLIs, including `-g -f` for several global Bakebooks
- [x] Commands run in the `bakefile.py`'s directory; `ctx.invocation_dir` documented with an example global command
- [x] Behaviour-change note: running from a subfolder without its own `bakefile.py` now runs the parent's commands
- [x] Agent-facing docs updated where they describe path resolution (architecture load flow, Bakebook context reference)
- [ ] The squash-merge message for the integration branch flags the behaviour change

## Comments

- New page `docs/site/usage/finding-bakefile.mdx` (resolution order, working directory, Global `bakefile.py`, `ctx.invocation_dir`, upgrading note); new troubleshooting page `troubleshooting/bakefile-not-found.mdx`.
- Updated README, `cli/bake.mdx`, `cli/bakefile.mdx`, `concepts/context.mdx`, `troubleshooting/{index,file-name-errors,bakebook-not-found}.mdx`, `skill.md`, `src/bake/bakebook/README.md`. `docs/reference/architecture.md` was already current from 01 and 02.
- Added the `uv cache clean bakefile` note from 02's handoff to `tests/README.md`.
- The repo has no changelog file; the behaviour-change note lives on the docs page's Upgrading section and goes in the squash-merge message (last box stays open until the merge).
- PR review fixes: `bakefile -g <subcommand>` with no global file now gives the same error as `bake -g` (closes 02's known gap); a relative `XDG_CONFIG_HOME` is ignored per the XDG spec.
