# 02: Editable blocks, upgrades and adoption

Status: resolved

Blocked by: 01

Spec: `.tracker/managed-content/spec.md`. Decision: `docs/adr/0006-managed-files-and-bake-lock.md`.

**What to build:** Templates can mark editable blocks the project owns. Hand content and Renovate bumps inside them survive template upgrades, untouched defaults follow new templates, and a hand `.gitignore` is adopted when the feature is turned on. `GitHubActionsTools` ships `renovate.json5` and `BaseSpace` ships `.gitignore`.

- [x] Grammar: `{% editable <name> %}<default>{% endeditable %}` (closing tag may repeat the name); on its own lines a block editable block (multi-line, may be empty), inside a line an inline one (single line)
- [x] Editable names are declared with the managed file; load fails on an undeclared name, a malformed or near-miss tag, a declared block missing from the template, or an editable block without fixed text on both sides
- [x] Read yields each editable block's content; the lock stores `editable.<name>` only for blocks that differ from the default (as normalised text)
- [x] Sync renders with blocks from the file when it reads, else from the lock when the hash matches; hash mismatch on a non-reading file exits 2, nothing written, with a hint naming the outgoing template's package to reinstall before `mc lock`, or `mc sync --force`
- [x] Untouched blocks take the new default on upgrade; an emptied block stays empty
- [x] Blocks carry over by name; a block gone from the template is dropped with a note
- [x] Edit inside an editable block: file untouched, lock records the block
- [x] Renovate bump in an editable block, then `setup-dev` or `lint`: bump kept, lock updated
- [x] Hand upgrade of bake with a current lock works; with an unlocked edit it exits 2 and `--force` drops the edit
- [x] `{% editable <name> adopt %}`, at most one per template (load error otherwise); a headerless file at the path is adopted with its content verbatim in that block; a second sync is up to date
- [x] A headerless file whose template has no adopt block exits 2 with nothing written; `--force` writes the template with default blocks
- [x] Markdown adoption tested with a fixture template
- [x] `GitHubActionsTools` ships `.github/renovate.json5`: `$schema` and `extends: ["config:recommended"]` fixed, an editable block for repo rules before the closing brace
- [x] `BaseSpace` ships `.gitignore`: adopt block first, then the standard lines (`.env*`, `*.local.md`, `*.local.toml`, `.claude/settings.local.json`, `.claude/worktrees/`, `.playwright-mcp/`, `.scratch`), then a trailing editable block where lines appended by other tools land
- [x] `FnoxSpace`'s `.gitignore` append still works with the toggle off and is a no-op with it on
- [x] The template test reads every rendered template back to exactly its defaults
- [x] `GLOSSARY.md` terms used: Editable block, Adoption

## Comments

Implemented in `src/bakelib/managed_content/engine.py` (parser, read, render, lock, sync) with templates `bakelib/space/managed/gitignore` and `renovate.json5`. Decisions made along the way:

- "Fixed text on both sides": the header and the end of the file count as fixed text, so a trailing editable block may end the file (the `.gitignore` needs this for lines other tools append). The load error is for two editable blocks with no fixed text between them.
- A file whose hash matches its lock entry takes its editable blocks from the lock, even when it also reads under the current template; `mc lock` keeps such entries as they are. Otherwise an untouched block would keep the old default after an upgrade that changes only defaults.
- Adopt blocks are a load error outside ignore files and markdown (ADR 0006, "Header and adoption"), and must be block editable blocks.
- Until 04, `{{ bakefile.` fails at load ("not supported yet"), and so does any other `{%` (including `{% raw %}`). `${{ ... }}` without `bakefile` stays fixed text.
- A managed file deleted by hand while in the lock is rewritten with its locked editable blocks.
- The `.gitignore` template is named `gitignore` in the package, since a file named `.gitignore` under `src/` would act as an ignore file. Block names: `base` (adopt) and `repo` in `.gitignore`, `rules` in `renovate.json5`.
- The template test rebuilds `bake.lock` with `mc lock` after the sync and fails when the file does not read back or any editable block differs from its default.
- A block editable block that a template upgrade makes inline keeps its content only when it is one line; multi-line content is dropped with a note and the block starts from its default.
- A block whose content holds the fixed text after it reads ambiguously (it splits at the first copy). This is left as a template-authoring rule rather than handled in sync. The spec's Sync section still says to read the file first, and should be updated to match the lock-first order above.
