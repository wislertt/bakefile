# 08: Pin bump by pattern

Status: resolved

Blocked by: 06

Spec: `.tracker/managed-content/spec.md`. Decision: `docs/adr/0007-child-spaces-extend-parent-templates.md` (Pin bumps).

**What to build:** This repo's `bake update` keeps every action pin in every template current, whether the template is a `.yml` file or a Python string, without markers, masking or scaffolds in the templates. It finds pins by pattern, has `actions-up` bump them in a throwaway workflow, and writes the bumped pins back.

- [x] The bump finds every `owner/repo@<40-hex sha> # <tag>` in the template files under `src/` (`.yml` and `.py`), including a pin whose SHA sits inside an inline editable block
- [x] Each unique pin becomes a `uses:` step in one throwaway workflow; `actions-up` runs on that workflow only, with the same minimum age as today; bumped pins are written back, keeping the action name, the editable tags and all other text; unchanged files are not rewritten
- [x] The marker masking and its tests are deleted; the expected files are regenerated after a bump as today
- [x] Tests with the `actions-up` subprocess patched: pins in a `.yml` template and in a Python string bumped, an editable tag around a pin kept, other text untouched, no pins means no `actions-up` run
- [x] This repo's `bake update` still bumps every template pin (checked on a copy with an old pin); `bake lint` and the full test suite pass

## Comments

- `scripts/template_pins.py` (`bump_template_pins`) replaces `scripts/template_actions.py` and its masking tests. The pattern allows an inline `{% editable <name> %}` between `@` and the SHA, so the tag stays where it was; the tag part matches `[\w.+-]+`, so a closing `{% endeditable %}` right after the version is untouched.
- `bake update` scans every `.yml` and `.py` under `src/` (not only `managed/`), so a child Space's insert string anywhere in the package is bumped too. In dry run it prints a note and skips `actions-up`, as before (dry run never ran it). The expected files are regenerated only when a pin changed.
- Checked for real on a copy of the workflow templates with `actions/checkout` set back to v4.1.1 in `security.yml` and in an inline editable block of a `.py` string: both went to v7.0.1, everything else unchanged.
