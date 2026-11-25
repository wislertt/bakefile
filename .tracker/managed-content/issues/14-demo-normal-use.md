# 14: Demo commands for normal use of managed files

Status: resolved

Blocked by: none (can start immediately)

Spec: `.tracker/managed-content/spec.md` (Testing Decisions, End to end; Further Notes; user story 88).

**What to build:** Temporary `bake` commands that walk a repo maintainer through normal use of managed files with real commands, on a disposable branch of this repo. Normal work goes through the existing `BaseSpace` commands (`setup-dev -ff`, `lint`, `update -ff`); `bake mc` appears only where the design needs it. Ticket 15 adds the error and escape-hatch steps and runs the final acceptance. Everything is deleted when the feature closes.

Layout:

- `scripts/demo/managed/`: two dummy templates, each with an editable block and fixed text
- a `DemoFiles` mixin in `scripts/demo/` whose `_get_managed_files()` extends `super()` with the two files (`ManagedFile("scripts.demo", ...)`), as a repo's own Bakebook adds its own files
- `DemoBakebook(MyBakebook)` in `scripts/demo/` with the step commands only, no managed files
- one line in `bakefile.py`, `demo = DemoBakebook()`; the demo files are live only on the demo branch, where a step makes `MyBakebook` inherit `DemoFiles`
- `.tracker/managed-content/e2e-runbook.md`: what each step does, what to look at, and the expected result

Each `bake -b demo step<N>` does the maintainer's action, runs the real `bake` commands as subprocesses, prints their output and exit code, checks them against the expected exit code and message (PASS or MISMATCH, MISMATCH exits non-zero), and names the next step. `bake -b demo all` runs every step in order.

- [x] Start: refuse unless `git status` is clean (no stash); remember the current branch; create `demo/managed-content-e2e`; commit a hand-written file at the first demo path that differs from its template
- [x] Add files: make `MyBakebook` inherit `DemoFiles` in `bakefile.py`, show the diff, commit
- [x] `bake setup-dev -ff` exits 2 on the differing existing file, and nothing is written, the new file included
- [x] `bake mc sync --force` writes both files and `bake.lock`; commit
- [x] `bake lint` and `bake setup-dev -ff` change nothing
- [x] An edit inside an editable block: `bake lint` locks it, `bake setup-dev -ff` keeps it
- [x] Template upgrade: change a demo template's fixed text, standing in for a parent release; the real `bake update -ff` writes the new text and keeps the block edit
- [x] End: switch back to the branch the start step remembered (it works from a worktree too), delete the demo branch, check `git status` is clean and `bake mc sync --dry-run` prints nothing
- [x] An agent runs `bake -b demo all`, every step PASS; each mismatch fixes the step or files a bug ticket; the run (date, commit, result) recorded under Comments
- [x] `bake lint` and the full test suite pass with `scripts/demo/` present

## Comments

- 2026-11-26, run on the ticket branch at 5b7b6ff (based on `feat/managed-content` adf2ed2): `bake -b demo all` exited 0, every step PASS, back on the starting branch (a worktree) with `git status` clean and the demo branch deleted. Step 7's real `bake update -ff` upgraded `ty` and `typer` in `pyproject.toml`, ran `pre-commit autoupdate`, `actions-up` and each example's `bake update -ff`; all of it was committed on the demo branch and dropped with it.
- First run found a demo bug, fixed in the steps: a `bake` subprocess inherited `_BAKE_REINVOKED` from the `bake -b demo` process, so it skipped re-invoking under the project's Python and failed to import `zerv`. The steps now start each `bake` with that variable removed and `VIRTUAL_ENV` cleared, as a maintainer's shell would.
- Layout: templates `scripts/demo/managed/alpha.toml` and `beta.yml` (written to `demo/alpha.toml` and `demo/beta.yml`), `DemoFiles` in `scripts/demo/files.py`, the steps in `scripts/demo/bakebook.py`, the PASS/MISMATCH check and the `bakefile.py` edit in `scripts/demo/check.py` (unit tests in `tests/unit/scripts/test_demo.py`). `DemoBakebook` imports `MyBakebook` from the loaded `bakefile` module, so `bakefile.py` imports it at the bottom, after `MyBakebook`: two lines plus a TEMP comment instead of one.
- The start step remembers the starting branch (or commit when detached) in a file in the worktree's own git dir, and refuses rather than stashes when the tree is dirty, since the stash stack is shared between worktrees. Demo commits use `--no-verify`; the steps run `bake lint` themselves. The end step also runs `uv sync --frozen` so the venv matches the starting branch's `uv.lock` after step 7's upgrade. Ticket 15's steps go between step 7 and the end step (`_steps()` in `bakebook.py`); the end step's number, and the `step8` hints, move with them.
