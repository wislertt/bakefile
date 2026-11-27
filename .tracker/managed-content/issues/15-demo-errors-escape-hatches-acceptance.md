# 15: Demo errors and escape hatches; final acceptance

Status: resolved

Blocked by: 11, 13, 14

Spec: `.tracker/managed-content/spec.md` (Testing Decisions, End to end; Further Notes on `edit()` and detach; user story 88).

**What to build:** The demo from ticket 14 also walks the rare cases a repo maintainer meets and how each is resolved, then the whole walk runs as the feature's final acceptance, after every other ticket. The new steps go between ticket 14's template upgrade and end steps, and the runbook gains them.

- [x] A hand edit to fixed text: `bake lint` and `bake setup-dev -ff` exit 2; fixes shown one by one, each checked: `git checkout -- <file>`; `bake mc sync --force` (locked blocks kept); an `edit()` override in `bakefile.py` (ticket 09), with lint and setup-dev passing; `.detach()` (ticket 13), with the edit kept through `lint` and `setup-dev -ff`
- [x] Re-attach: remove `.detach()`; exit 2; `bake mc sync --force` resumes management
- [x] Gotcha: an unlocked block edit plus a fixed-text edit, then `--force`, loses the block edit
- [x] Drop: remove a hand-edited demo file from `DemoFiles`; sync keeps it with a note (ticket 12); an unchanged dropped file is deleted
- [x] Final acceptance: an agent runs `bake -b demo all` after tickets 01 to 14 are resolved, every step PASS; each mismatch fixes the step or files a bug ticket; the run (date, commit, result) recorded under Comments, ending back on the starting branch with `git status` clean
- [x] `bake lint` and the full test suite pass

## Comments

- 2026-11-26, final acceptance on the ticket branch at b702324 (based on `feat/managed-content` 22a49e0, tickets 01 to 14 resolved): `bake -b demo all` exited 0, steps 1 to 15 all PASS (66 checks, no MISMATCH), back on the starting branch (a worktree) with `git status` clean and the demo branch deleted. `bake lint` exits 0; `bake test` 2986 passed, 3 xfailed.
- First run found a demo bug, fixed in step 8: the "nothing written" check compared `git status --porcelain` output after `.strip()` had removed its leading space. No product bug found.
- New steps 8 to 14 sit between the upgrade (7) and the end step, now step 15: fixed-text edit refused by lint and setup-dev then fixed by `git checkout` (8), by `mc sync --force` (9), by an `edit()` override in `bakefile.py` (10), by `.detach()` (11); re-attach (12); the `--force` gotcha (13); dropping both files (14). The `bakefile.py` and `DemoFiles` edits are pure functions in `scripts/demo/check.py` (`override_managed_file`, `remove_override`, `drop_demo_files`), unit tested in `tests/unit/scripts/test_demo.py`.
- Worth knowing: re-attaching through `--force` also loses the step 6 block edit, since detaching dropped the lock entry and `--force` renders the lock (or the defaults). That follows the spec; step 12 checks it and the runbook says so.
- 2026-11-26: `edit()` was removed (ticket 16), so the demo dropped its `edit()` step: detach is now step 10, re-attach 11, the gotcha 12, dropping both files 13, and the end step 14.
