# 04: Bakefile values, `update` ordering, docs and cleanup

Status: resolved

Blocked by: 02, 03

Spec: `.tracker/managed-content/spec.md`. Decision: `docs/adr/0006-managed-files-and-bake-lock.md`.

**What to build:** Templates can contain bakefile values that child Spaces extend through hooks, `bake update` writes managed files with the templates it just installed, users have docs for the whole feature, and the PoC history is removed.

- [x] `{{ bakefile.<name> }}` resolved by name on the Bakebook (a setting, or a hook children extend with `super()`); names declared with the managed file; load fails on an undeclared name or a value without fixed text on both sides
- [x] Bakefile values match anything when read, are always re-rendered and never locked; a changed value is rewritten with a note, a hand edit inside one is reverted with a note; a removed hook value empties it and its banner stays
- [x] A multi-line value sits alone on its line and is indented to the marker's column; a default may contain a value
- [x] `{% raw %}...{% endraw %}` passes text through untouched
- [x] Tested with fixture templates
- [x] `BaseSpace`'s `.gitignore` gets a hook-backed bakefile value right after the standard lines, empty in `BaseSpace`, so a child Space adds standard lines with `super()`; tested with a made-up child Space that adds a line, checking the line lands after the standard lines, the repo blocks are kept and the parent's standard lines still upgrade
- [x] `update` locks in-process before any upgrade, and after tools and dependencies are upgraded runs `bake mc sync` as a fresh subprocess so the new templates are used
- [x] Renovate bump then `update`: bump kept, lock updated
- [x] User docs: toggle, `managed-content` commands and exit codes, `bake.lock`, editable blocks and adoption, authoring templates (shared oxfmt style, header table, template-authoring rules from the spec's Further Notes)
- [x] `history/` deleted, with its exclusions in `pyproject.toml`, `.prettierignore` and `.pre-commit-config.yaml`
- [x] `GLOSSARY.md` terms used: Bakefile value

## Comments
