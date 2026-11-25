# 09: Child Spaces change a parent template

Status: resolved

Blocked by: 07

Spec: `.tracker/managed-content/spec.md`. Decision: `docs/adr/0007-child-spaces-extend-parent-templates.md`. Prototype: `demo/inheritance/` on the local branch `archive/managed-content-demo` (see its `check.py` for every scenario; `git show archive/managed-content-demo:demo/inheritance/check.py`).

**What to build:** A child Space shapes a parent's template without forking it. It takes the managed file from `super()._get_managed_files()` and returns a changed copy: it inserts text at a template hook the parent marked, replaces an editable block's default, or edits text that appears exactly once. What a child inserts belongs to the template, so repos can edit the editable blocks inside it and those edits survive. Templates may also be Python strings. No bakelib Space uses this yet; test Spaces prove it, and company Spaces downstream are the users.

Shape from the prototype:

```python
class JobChild(ParentSpace):
    def _get_managed_files(self) -> dict[str, ManagedFile]:
        files = super()._get_managed_files()
        files[SECURITY] = files[SECURITY].insert("extra_jobs", CHILD_JOB)
        return files
```

- [x] `{% hook <name> %}` on its own line marks a template hook; it renders to nothing and is not part of the read pattern; a template hook that appears twice fails at load
- [x] `insert(hook, text)` places the text just above the template hook's marker, so inserts land in MRO order, each after those of the Spaces it builds on; inserted text is indented relative to the template hook's column; it fails on an unknown template hook or a block name the template already has
- [x] `set_default(block, text)` replaces an editable block's default (one line for an inline block); it fails on an unknown block or a block that holds a template hook
- [x] ~~`edit(old, new)` replaces text that appears exactly once and fails otherwise~~ (superseded: removed in ticket 16)
- [x] A managed file can take its template as a string instead of a package file; the template key stays `<distribution>:<name>`
- [x] Every mistake raises at the child's call with the template key in the message; a command reports it as exit 2 with nothing written
- [x] `TemplateSuite` renders each concrete Space's own combination of a managed file, not one case per template, so a child's inserts are checked like a parent's template, block-name snapshot included; it skips Python modules in `managed/` when it looks for templates no Space writes
- [x] Tests at the Space-command seam with test Spaces: inserts from two children in MRO order and its reverse, a grandchild inserting at a template hook its parent's insert brings, a string template rendering like the same file, a repo edit and a Renovate bump inside an insert kept across sync and an upgrade, a child's switch turning its insert off, and each mistake exiting 2 with nothing written
- [x] Docs for Space authors: template hooks, the three methods, strings next to files, and switching an insert off; `bake lint` and the full test suite pass

## Comments

- 2026-11-26: `ManagedFile` gained `text` (a template given as a string) and `edited_text` (the template after a child's `insert`, `set_default` or `edit`); `read_template()` returns the edited text, else the string, else the package file, normalised. Each method validates eagerly and returns `replace(self, edited_text=...)`, so mistakes raise at the child's call. `BaseSpace._managed_content()` now calls `_get_managed_files()` inside `exit_on_error()`, so sync and lint report a child's mistake as exit 2 with nothing written.
- 2026-11-26: Inserted text is indented to the hook marker's column line by line, except `{% editable %}` and `{% endeditable %}` tag lines, which stay at column 0 because the grammar only reads a block editable block from tags at column 0. Without that, an insert holding a block editable block failed to parse. Hook markers are stripped before parsing, so they never reach the read pattern.
- 2026-11-26: `TemplateSuite` now groups cases by (template, path, `ManagedFile`), and the `ManagedFile` includes the changed text, so each distinct combination is its own case. An unchanged declaration keeps `<template>.expected`; a changed one is `<template>@<Space>.expected` (and `.blocks.expected`), named after the most-base Space that produces it. `_managed_files_of` now fills field defaults on the uninitialised instance, so a child's switch (a field) reads its default; construction still skips validation. Undeclared `.py` files in `managed/` are not reported as templates no Space writes, and string templates need no file on disk.
- 2026-11-26: Tests: `tests/unit/bakelib/space/test_child_spaces.py` (fixtures `hooks.yml`, `hooks_v2.yml`) and new `TemplateSuite` cases in `tests/unit/bakelib/managed_content/test_testing.py`. No bakelib template has a hook yet (ticket 10), so the docs example uses a hypothetical parent `ci.yml`.
- 2026-11-26: `edit(old, new)` was removed (ticket 16): it targeted raw template text, which is no part of the template's contract, so it broke whenever the parent reworded that text. `insert`, `set_default` and `.detach()` stay. A repo needing different fixed text asks the template's owner for a hook or an editable block and detaches the file meanwhile.
