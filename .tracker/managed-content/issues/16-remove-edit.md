# 16: Remove `ManagedFile.edit()`

Status: resolved

Blocked by: 09, 15

Spec: `.tracker/managed-content/spec.md` (Child Spaces change a parent template; Further Notes). Decision: `docs/adr/0007-child-spaces-extend-parent-templates.md` (amended 2026-11-26).

**What to build:** Remove `ManagedFile.edit(old, new)`. It targets raw template text, which is no part of the template's contract, so it breaks whenever the parent rewords that text, and nothing in `src/` uses it. Keep `insert(hook, text)` and `set_default(block, text)`, which target named template hooks and editable blocks, and `.detach()`. A repo that needs different fixed text asks the template's owner for a template hook or an editable block (then uses `insert`/`set_default` or edits the block), and detaches the file meanwhile.

- [x] `edit` gone from `ManagedFile`, with its tests; a test that used it to stand in for a template upgrade now gives the upgraded template as a string
- [x] The demo drops its `edit()` step, so the fixes for a fixed-text edit are revert, `--force` and detach; detach starts from the hand edit itself; 14 steps, `all` still runs them, each step still stages for review
- [x] Docs, spec, runbook, ADR 0007 (dated amendment) and ticket 09 (dated comment) say `edit()` is gone and give the guidance above; `bake lint` and the unit tests pass

## Comments

- 2026-11-26: Demo steps are now: detach (10), re-attach (11), the `--force` gotcha (12), dropping both files (13), end (14). `override_managed_file` and `remove_override` in `scripts/demo/check.py` are unchanged. Spec user story 77 is struck through with a dated note rather than deleted, so later story numbers stay. Resolved tickets 10, 11, 13 and 15 still mention `edit()` in their history and are left as written.
