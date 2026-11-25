# 12: Keep a changed dropped file

Status: resolved

Blocked by: none (can start immediately)

Spec: `.tracker/managed-content/spec.md` (Sync, user story 87). Decision: `docs/adr/0006-managed-files-and-bake-lock.md` (amended 2026-11-26).

**What to build:** Dropping a file never deletes hand edits. A file `bake.lock` lists that no Space produces any more is deleted only when it still matches its locked hash. A file changed since bake last wrote or locked it is kept as it is, with a note, and its lock entry is dropped, so it becomes a hand file.

- [x] `mc sync`, `setup-dev` and `update` delete a dropped file that matches its locked hash, as today
- [x] A dropped file whose content differs from its locked hash is kept with a one-line note naming the path, and its lock entry is dropped; the next sync says nothing about it
- [x] `--dry-run` lists only the files it would delete; `--force` does not change the rule
- [x] Tests at the Space-command seam: an unchanged dropped file deleted, a changed one kept with the note and gone from `bake.lock`, a second sync silent, and a later hand file at a deleted path still left alone
- [x] Docs: the dropped-file paragraph says when a file is kept; `bake lint` and the full test suite pass

## Comments

- The rule lives in `plan_sync` (`src/bakelib/managed_content/engine.py`), so `mc sync`, `setup-dev` and `update` share it. The hash compare uses normalised text, so a CRLF or BOM checkout of an untouched file is still deleted. A dropped file that is not UTF-8 counts as changed and is kept, rather than failing the sync.
- Note text: `<path>: kept, changed since bake wrote it and no Space produces it any more; it is now a hand file`. `--dry-run` prints it too, and does not write the lock.
- `lint` does not report a changed dropped file (nothing on disk would change); its stale lock entry stays until the next sync drops it, which CI tolerates like any stale lock.
