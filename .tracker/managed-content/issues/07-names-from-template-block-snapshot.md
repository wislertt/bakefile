# 07: Read block and value names from the template; block-name snapshot

Status: resolved

Blocked by: 06

Spec: `.tracker/managed-content/spec.md`. Decisions: `docs/adr/0006-managed-files-and-bake-lock.md`, `docs/adr/0007-child-spaces-extend-parent-templates.md`.

**What to build:** A Space author writes each editable block and bakefile value name once, in the template. A managed file declares only where its template comes from; the engine reads block and value names from the text. Because block names are the keys in `bake.lock`, `TemplateSuite` guards them instead: it compares each managed file's block names with an expected snapshot, so a rename that would drop every repo's edits to that block fails until it is accepted in review.

- [x] A managed file declaration has no editable block or bakefile value names; every bakelib Space and test drops them
- [x] Load no longer checks names against a declaration; it still fails on two editable blocks with one name, and a template that uses a bakefile value no Space gives still exits 2 with nothing written
- [x] `TemplateSuite` compares each managed file's editable block names with an expected snapshot next to its expected file; a missing snapshot is written and a changed one fails, both regenerated with `BAKE_UPDATE_EXPECTED=1`, and a stale snapshot is reported like a stale expected file
- [x] Tests at the Space-command seam: a template with an undeclared block and value renders and locks as before; a missing value exits 2. `TemplateSuite` tests: a renamed block fails against its snapshot, and regenerating accepts it
- [x] Docs drop the declarations and describe the snapshot; `bake lint` and the full test suite pass

## Comments
