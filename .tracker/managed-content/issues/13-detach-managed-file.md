# 13: Detach a managed file

Status: resolved

Blocked by: 09, 12

Spec: `.tracker/managed-content/spec.md` (Detached files, user stories 85 and 86). Decision: `docs/adr/0006-managed-files-and-bake-lock.md` (amended 2026-11-26). Glossary: Detached file.

**What to build:** A repo takes a managed file over by hand without losing it. Its Bakebook returns the file's entry from `_get_managed_files()` with `.detach()`, and bake stops touching that file until the repo removes the call. Use it for text outside the editable blocks a repo must own: a fix that cannot wait for the Space's release, or a file that has diverged too far for `edit()` (ticket 09), which suits a small temporary change only.

```python
def _get_managed_files(self) -> dict[str, ManagedFile]:
    files = super()._get_managed_files()
    files["README.md"] = files["README.md"].detach()
    return files
```

- [x] `ManagedFile` has a `detached` field, default off, and `.detach()` returns a copy with it set, in the style of ticket 09's methods
- [x] Sync, lock and check skip a detached path: its template is not loaded (a missing or broken template does not block), nothing is written, compared or deleted, and the file is left as it is, header included
- [x] A detached path's lock entry is dropped with a one-line note when it goes; later runs say nothing; a detached path with no file gets nothing written
- [x] Removing `.detach()`: a file whose header and fixed text match reads, keeps its editable blocks and is locked; otherwise exit 2 with the `--force` hint, and `--force` writes the template
- [x] Tests at the Space-command seam: a fixed-text edit kept through `mc sync`, `lint`, `setup-dev` and `update` once detached; the note once; re-attach clean and through `--force`; a detached path with no file; a detached file whose template is missing
- [x] Docs: when to use `edit()` and when to detach, and how to re-attach; `bake lint` and the full test suite pass

## Comments

- `ManagedFile.detached` and `.detach()` (`src/bakelib/managed_content/engine.py`). `load_templates` skips detached paths, so a missing or broken template never loads. `drop_detached()` removes their lock entries before `relock` and `plan_sync`, so neither keeps nor deletes them (`plan_sync` would otherwise treat them as dropped files). The note comes from whichever command first sees the entry: `lint` and `update` from their lock step, `mc sync` and `setup-dev` from the plan. Text: `<path>: detached, bake no longer manages it; its bake.lock entry is dropped`.
- Re-attach needed no code: with no lock entry, the existing unlocked-file path reads a matching file and locks it, and exits 2 with the `--force` hint otherwise.
- `BaseSpace._get_managed_values()` passes `Fetch.NEVER` to the `.gitignore` stack section when `.gitignore` is detached or absent, so a detached `.gitignore` is never fetched for (otherwise `mc sync --refresh` in `update` would still hit github/gitignore). This calls `_get_managed_files()` a second time per command; `FLAKY_SPACES` in `test_testing.py` counted hook calls, so it now flips on whether `flaky.yml` exists instead.
- Tests: `TestDetachedFile` and `TestDetachedGitignore` in `tests/unit/bakelib/space/test_managed_content.py`. `update` is covered by its in-process lock plus a direct `mc sync --refresh` standing in for the subprocess. Docs: "Detaching a file" in `docs/site/bakelib/managed-content.mdx`.
