# Child Spaces extend a parent template through template hooks, block defaults and checked edits

ADR 0006 let a child Space change a parent template in two ways only: a `bakefile.*` value or a whole-file override. That fails the common case of a child adding a job or a step that the repo must be able to edit: a value is re-rendered on every write and never locked, so a repo's `runs-on` change or a Renovate pin bump inside a child's job would be reverted. Many users at many companies, each with its own policy, need child Spaces to shape a shared template without forking it. This ADR replaces the "two ways only" rule and the `values=` declaration of ADR 0006 (its Plugins section), the "never template text" part of the same section, and its rejection of a transform function on `ManagedFile`.

## Changing a parent template

A child takes the `ManagedFile` from `super()._get_managed_files()` and returns a changed copy, so changes apply in MRO order, and a Space builds on the Spaces it inherits from:

- `insert(hook, text)` adds text at a template hook (`{% hook <name> %}`) the parent marked. The text becomes part of the template, so editable blocks inside it are locked and kept like the parent's own. The marker renders to nothing. Inserted text is indented relative to the template hook's column, the same rule as a value.
- `set_default(block, text)` replaces the default of an editable block. A block that holds a template hook cannot be replaced, only extended at the hook, so one child cannot wipe out what another inserted.
- `edit(old, new)` replaces text that must appear exactly once. It is the escape hatch for a need the parent did not plan for.

Every mistake (an unknown template hook or block, an edit whose text appears zero or several times, a block name the template already has) raises at the child's own call, so it fails in the Space author's CI, not in a user's repo. A repo that does not want a child's insert turns it off through a switch the child offers; there is no removal by name. Template hooks are optional: a parent without them can still be changed through `set_default` and `edit`.

## Template text and declarations

A template is text, read from `<package>/managed/<name>` or given as a Python string. Files are the norm for a parent template, because the editor checks them and a review shows the output's shape; strings suit the small snippets a child inserts. The template key stays `<distribution>:<name>` (amended 2026-11-27, see below).

A managed file declares no editable block or `bakefile.*` value names: the engine reads them from the text. A template that uses a value no Space gives still fails at load. Block names are the keys in `bake.lock`, so a rename drops every repo's edits to that block; `TemplateSuite` guards it with a snapshot of each template's block names, which a rename changes in review.

## Pin bumps

Action pins (`owner/repo@<sha> # <tag>`) are found by pattern in every template file, `.yml` or `.py`, written into a throwaway workflow for actions-up, and the bumped pins are written back. Templates never pass through actions-up, so they need no marker masking and no scaffold to look like a workflow.

## Considered Options

- **A hook-backed `bakefile.*` value for child content** (ADR 0006). Rejected for content the repo edits: values are never locked, so its edits and pin bumps are reverted.
- **Only planned extension points, no `edit`** (ADR 0006's rejection of a transform function). Rejected: a company Space would wait for a bakefile release for every unplanned need. The coupling to exact text remains, but a mismatch now fails at the child's call instead of silently.
- **Separate `_get_managed_inserts()` and `_get_managed_defaults()` hooks**, applied by the engine (the first prototype). Rejected: the engine chose the order and errors surfaced away from the child's code; editing the `ManagedFile` through `super()` gives MRO order for free.
- **Declaring `editable=` and `values=` with each managed file and insert** (ADR 0006). Rejected: every name lived twice, and the block-name snapshot guards renames without it.
- **A `{% fragment %}` marker** dropping a `jobs:` scaffold above a child's snippet so actions-up could read its pins. Rejected: a marker existed only for one tool, and strings could not be bumped at all.

## Amendment, 2026-11-26: `edit` removed

`edit(old, new)` is removed. It targeted raw template text, which is no part of the template's contract, so a child's edit broke whenever the parent reworded that text, and no Space in bakelib used it. `insert` and `set_default` stay, since they target named template hooks and editable blocks. A repo that needs different fixed text asks the template's owner for a template hook or an editable block, and detaches the file (ADR 0006) meanwhile. The text above describes the decision as first made; read its `edit` parts, and the rejection of "only planned extension points, no `edit`", as superseded by this note.

## Amendment, 2026-11-27: `from_text`

A template given as a string goes through `ManagedFile.from_text(text, package=..., name=...)`; the constructor no longer takes `text=`, so it always reads a file. Give `package` and `name` together, for a Space's string template, or neither, for a repo's own template, keyed `repo:<path>`. Keys are `<package>:<name>` as declared (ADR 0006, amendment 2026-11-27).
