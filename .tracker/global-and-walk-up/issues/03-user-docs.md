# 03: User docs for walk-up and Global `bakefile.py`

Status: ready-for-agent

Blocked by: 02 (Global `bakefile.py`)

Spec: `.tracker/global-and-walk-up/spec.md`. Decision: `docs/adr/0005-one-bakefile-per-run-no-merging.md`.

**What to build:** A user reading the README or the docs site learns how `bake` picks a `bakefile.py`, how to set up a Global `bakefile.py`, and how to write commands that act on the Invocation directory. Users upgrading learn that running from a subfolder now finds a parent `bakefile.py`.

- [ ] Resolution order documented: `-g`, `-C` exact, walk-up (with `-f`), then global fallback
- [ ] Global directory location and override (`BAKE_CONFIG_DIR`, `XDG_CONFIG_HOME`), with the dotfiles symlink example and `bakefile -g init`
- [ ] `-g` on both CLIs, including `-g -f` for several global Bakebooks
- [ ] Commands run in the `bakefile.py`'s directory; `ctx.invocation_dir` documented with an example global command
- [ ] Behaviour-change note: running from a subfolder without its own `bakefile.py` now runs the parent's commands
- [ ] Agent-facing docs updated where they describe path resolution (architecture load flow, Bakebook context reference)
- [ ] The squash-merge message for the integration branch flags the behaviour change

## Comments
