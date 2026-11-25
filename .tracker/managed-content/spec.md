# Managed content

Status: resolved

Decisions: `docs/adr/0006-managed-files-and-bake-lock.md`, and `docs/adr/0007-child-spaces-extend-parent-templates.md` for how child Spaces change a parent template. Vocabulary: `GLOSSARY.md` (Managed content section). Background, PoC code and the dropped v1 lived in `history/`, deleted in ticket 04; git history before that commit has it (it uses old words, "hole" is now editable block and "slot" is a hook-backed `bakefile.*` value).

## Problem Statement

About 19 repos use bakelib, and they copy the same config and docs by hand. The copies drift. A survey (2026-11-22) found `.releaserc.mjs` identical in 13 repos, `renovate.json5` identical in 11 of 14, `.prettierrc.json` still in 15 repos although `lint` runs oxfmt everywhere, and no two `.gitignore` files alike. When a Space changes what a project needs, the maintainer fixes every repo by hand, nothing tells them a repo has fallen behind, and nothing removes what an older Space version left behind.

## Solution

A Space declares managed files: files it renders from a template that ships in its package. The project edits only the editable blocks marked in the template; bake owns the rest. `setup-dev` and `update` write managed files, `lint` reports drift, and `bake.lock` at the project root records which files bake wrote and which editable blocks the project changed, so hand content and Renovate bumps survive template upgrades, and files a Space no longer produces are deleted unless the project changed them.

A project that must own text outside the editable blocks detaches that file in its own Bakebook: bake keeps the file as it is and stops writing, checking and deleting it, until the project removes the detach.

Day to day, the existing commands (`setup-dev`, `lint`, `update`) handle managed files; the `mc` commands are for the rare cases, such as `--force` after a hand edit to fixed text. A temporary walk through this lifecycle with real commands, on a disposable branch of this repo, accepts the feature at the end.

A child Space shapes a parent's template without forking it: it adds text at a template hook the parent marked, or replaces an editable block's default. What a child adds belongs to the template, so its editable blocks are locked and kept like the parent's. Many users at many companies, each with its own policy, can then build on the same bakelib templates.

The feature is off by default during beta behind `bake_manage_content`.

First content:

- `BaseSpace`: `oxfmt.config.ts` (the shared formatter style, with an editable block for ignore patterns) and `.gitignore` (the github/gitignore stack section, the Space lines `.env*`, `*.local.md`, `*.local.toml`, `.claude/settings.local.json`, `.claude/worktrees/`, `.playwright-mcp/`, `.scratch` and the ssh key patterns, then one editable block).
- `GitHubActionsTools`: `.github/renovate.json5` and the security workflow (`.github/workflows/security.yml`).
- `PythonSpace` and `PythonLibSpace`: no file of their own. The Python workflow templates (test, pre-commit and publish) ship unused; a later Space, outside this spec, will write them, and until then a repo declares them in its own bakebook (amended 2026-11-26: `PythonSpace` wrote the pre-commit and test workflows and `PythonLibSpace` the publish workflow).
- `ZervGitHubActionsTools`, a new child Space of `GitHubActionsTools` for repos that version with zerv in GitHub Actions: `.releaserc.mjs`, `.github/workflows/semantic-pull-request.yml` and the ci and cd workflows (`.github/workflows/ci.yml`, `.github/workflows/cd.yml`).

Workflow templates start relaxed: anything that varies between repos sits in an editable block (each pin and `runs-on` an inline one; the steps around them are fixed text), and templates tighten only when a need shows. This repo turns the feature on and runs every managed file before the release.

## User Stories

1. As a repo maintainer, I want config shared by every repo to come from the Space I already use, so that I stop copying files by hand.
2. As a repo maintainer, I want `bake setup-dev` to write the managed files my Spaces declare, so that a new or existing repo gets them without extra steps.
3. As a repo maintainer, I want `bake update` to bring managed files up to the templates of the newly installed bakefile and plugins, so that one command upgrades both tools and config.
4. As a repo maintainer, I want `bake lint` to fail when a managed file differs from what its Spaces would write now, so that I notice drift before merging.
5. As a repo maintainer, I want drift reported against the files as committed, before any formatter runs, so that a formatter cannot hide or cause it.
6. As a repo maintainer, I want `bake mc sync` to write managed files on demand, so that I can fix drift without a full `setup-dev`.
7. As a repo maintainer, I want `bake mc sync --dry-run` to show what would change without writing, so that I can review an upgrade first.
8. As a repo maintainer, I want `bake mc lock` to rebuild `bake.lock` from the files, so that a conflicted, missing or hand-edited lock is easy to fix.
9. As a repo maintainer, I want `managed-content` commands also reachable as `mc`, so that I type less.
10. As a repo maintainer, I want managed content off unless I set `bake_manage_content = True` in `bakefile.py` or `BAKE_MANAGE_CONTENT=true`, so that the beta does not touch repos that did not opt in.
11. As a repo maintainer with the toggle off, I want no writes, no drift check, no `bake.lock` and no output from managed content, so that nothing changes for me.
12. As a repo maintainer with the toggle off, I want `bake mc sync` to exit nonzero with a hint on how to turn it on, so that I know why nothing happened.
13. As a repo maintainer, I want my content inside an editable block kept across template upgrades, so that local additions survive.
14. As a repo maintainer, I want an editable block I never touched to follow the template's new default, so that pinned defaults (such as a tool version) upgrade with the Space.
15. As a repo maintainer, I want an editable block I emptied to stay empty across upgrades, so that removing a default is respected.
16. As a repo maintainer, I want a Renovate bump inside an editable block kept on the next `setup-dev`, `lint` or `update`, so that Renovate and bake do not fight.
17. As a repo maintainer, I want Renovate to need no config for `bake.lock`, so that the lock costs me nothing in Renovate.
18. As a repo maintainer, I want `lint` (and so the pre-commit hook) to relock, so that the lock catches up on my next local commit.
19. As a repo maintainer, I want CI to tolerate a stale `bake.lock`, so that a Renovate PR does not fail for a lock it cannot update.
20. As a repo maintainer, I want an edit outside editable blocks reported with the file and the first out-of-place line (`expected '<line>', but line N is '<text>'`), so that I can find it fast.
21. As a repo maintainer, I want `bake mc sync --force` to overwrite an edit outside editable blocks, with the dropped text visible in git diff, so that I can restore a file deliberately.
22. As a repo maintainer, I want an upgrade to refuse (exit 2, nothing written) when the file has unlocked edits and the template changed, with a hint naming the package to reinstall or offering `--force`, so that bake never silently loses my edits.
23. As a repo maintainer, I want an upgrade to succeed whenever the lock was current, even when I upgraded bake by hand, so that I do not have to use `bake update`.
24. As a repo maintainer, I want any error to leave every file untouched, so that a failed run never leaves a half-written repo.
25. As a repo maintainer, I want exit code 0 for clean, 1 for drift and 2 for an error, so that scripts and CI can tell them apart.
26. As a repo maintainer, I want a file that bake wrote and no Space produces any more deleted along with its lock entry, so that old Space versions leave nothing behind.
27. As a repo maintainer, I want a file I recreate at a deleted path left alone, so that bake does not claim a file it did not write.
28. As a repo maintainer, I want a hand `.gitignore` adopted into the managed file with its content kept verbatim, so that turning the feature on keeps my ignore rules.
29. As a repo maintainer, I want my repo's own `.gitignore` rules placed after the lines bake writes, so that my rules still win.
30. As a repo maintainer, I want a line another tool appends to `.gitignore` to land in an editable block, so that it is not drift.
31. As a repo maintainer, I want a headerless file at a managed path that cannot be adopted to exit 2 with nothing written, and `--force` to replace it, so that bake never mangles a structured file.
32. As a repo maintainer, I want each managed file to start with the header `managed by bakefile; edit only the parts marked "editable"` in the file's comment syntax, so that anyone opening it knows the rules.
33. As a repo maintainer, I want visible `(editable)` markers next to each editable block, so that I can see where I may edit.
34. As a repo maintainer, I want a Windows checkout with CRLF line endings, a BOM or a missing final newline not to count as drift, so that line-ending settings do not break lint.
35. As a repo maintainer, I want bake to rewrite a file only when its content actually changes, so that runs do not create noise in git.
36. As a repo maintainer, I want managed files already in the shared oxfmt style, so that `lint` and format-on-save in my editor leave them alone.
37. As a repo maintainer whose repo formats managed files differently, I want lint to report drift and `mc sync --force` to restore them, so that the cause is clear.
38. As a repo maintainer using `ZervGitHubActionsTools`, I want the semantic pull request workflow managed, with the pinned action in an inline editable block, so that PR titles are validated in every such repo and Renovate and `actions-up` bumps survive.
39. As a repo maintainer using `GitHubActionsTools`, I want `.github/renovate.json5` managed with an editable block for my own rules, so that the shared base stays current.
40. As a repo maintainer using `ZervGitHubActionsTools`, I want `.releaserc.mjs` managed, so that release rules stay identical across repos.
41. As a repo maintainer, I want `oxfmt.config.ts` managed by `BaseSpace`, so that every repo formats the same way.
42. As a repo maintainer using fnox, I want the fnox cache to stay gitignored while managed content is off, so that the toggle does not weaken secret safety.
43. As a Space author, I want to declare a managed file as a package anchor and a template name, or as template text in a Python string, so that the template ships in my package and works from any distribution.
44. As a Space author, I want managed files to compose through a hook extended with `super()`, so that they work like mise tools and diamonds resolve by MRO, and a child's changes to a parent template apply in MRO order.
45. As a Space author, I want the most-derived Space to win a path, so that a child can replace a parent's file whole.
46. As a Space author, I want `{{ bakefile.<name> }}` values filled from a setting or a hook children extend, so that I can offer planned extension points without forking the template.
47. As a Space author, I want a hand edit inside a `bakefile.*` value reverted with a note, so that bake-owned values stay owned by bake.
48. As a Space author, I want a multi-line `bakefile.*` value indented to its marker's column, so that hooks return plain text.
49. As a Space author, I want template load to fail on a malformed or near-miss tag, more than one adopt block, a template hook that appears twice, a bakefile value no Space gives, or an unsupported file type, so that template mistakes surface in bake's CI, not in user repos.
50. As a Space author, I want `{% raw %}` to pass text through untouched, so that a template can contain tag-like text.
51. As a Space author, I want editable blocks to carry over by name, with a removed block dropped with a note, so that renaming or removing blocks is predictable.
52. As a bakefile maintainer, I want every shipped template rendered, checked with `oxfmt --check` and read back in CI, so that a template that would drift in user repos never ships.
53. As a bakefile maintainer, I want CI to prove every template is in the built wheel, so that packaging mistakes do not reach users.
54. As a bakefile maintainer, I want this repo's own lint to leave template sources alone, so that oxfmt does not reformat files that contain tags.
55. As a repo maintainer turning the feature on, I want a headerless file that already equals what bake would write (apart from the header) taken over with a note, so that I run `--force` only where a file really differs.
56. As a repo maintainer, I want my own oxfmt ignore patterns in an editable block of the managed `oxfmt.config.ts`, so that a repo that authors templates can keep them out of the formatter.
57. As a repo maintainer using `GitHubActionsTools`, I want the security workflow (trivy and gitleaks) managed, so that every repo scans the same way.
58. As a repo maintainer of a Rust repo, I want the docs to show the cargo audit job to add in the security workflow's trailing editable block, so that Rust dependencies are scanned too without `RustSpace` knowing about GitHub Actions.
59. As a repo maintainer using `PythonSpace`, I want the pre-commit and test workflows managed, so that CI for Python repos stays identical across repos. (Amended 2026-11-26: the templates ship for this, but the repo declares them itself until a later Space writes them.)
60. As a repo maintainer using `PythonLibSpace`, I want the publish workflow managed, so that every library publishes through `bake publish` the same way. (Amended 2026-11-26: as story 59.)
61. As a repo maintainer using `ZervGitHubActionsTools`, I want the ci and cd workflows managed, with the zerv versioning and release jobs from the Space, so that the shared release flow stops drifting between repos.
62. As a repo maintainer, I want the jobs my Spaces add to ci and cd (test, pre-commit, publish) in an editable block that follows my Spaces until I edit it, so that a Python library and a Rust repo each get the right jobs and I can still change them.
63. As a repo maintainer, I want anything that varies between repos in a workflow (action pins, `runs-on`, OS matrix, Python versions, repo-only jobs) in editable blocks, so that Renovate bumps and repo choices survive without new settings.
64. As a Space author, I want a rule that a bakefile value never carries a pinned action, and a template hook for content that does, so that bake and Renovate never fight over a pin bake re-renders.
65. As a bakefile maintainer, I want this repo to run with managed content on before the release, so that the first real user is us.
66. As a bakefile maintainer, I want this repo's `bake update` to bump action pins in every template, `.yml` files and Python strings alike, so that template pins stay current without markers or scaffolds in the templates.
67. As a Space author, I want to give every bakefile value as text in one mapping, so that a reader sees what fills each value without knowing a naming rule.
68. As a Space author, I want the command to tell my value code whether it may fetch, so that `lint` never needs the network and only a sync fetches.
69. As a repo maintainer, I want `bake mc sync --refresh` to fetch network-backed values again from their latest upstream, so that I pick up upstream fixes without a full `bake update`.
70. As a Space author, I want to mark a template hook (`{% hook <name> %}`) in a template, so that child Spaces can add text at a place I planned.
71. As a Space author writing a child Space, I want to insert text at a parent's template hook, so that I add a job, a step or an input without copying the parent template.
72. As a Space author writing a child Space, I want several inserts at one template hook to land in MRO order, each after those of the Spaces it builds on, so that the result is predictable.
73. As a Space author writing a child Space, I want editable blocks and template hooks inside my inserted text to work like the parent's, so that repos can edit my job and grandchildren can extend it.
74. As a repo maintainer, I want my edits and Renovate bumps inside a child Space's inserted job kept across syncs and upgrades, so that a child's content is as safe to edit as the parent's.
75. As a Space author writing a child Space, I want to replace the default of a parent's editable block, so that my company's policy (a schedule, a severity) becomes the default its repos start from.
76. As a Space author, I want a block that holds a template hook to refuse a new default, so that one child cannot wipe out what another inserted.
77. ~~As a Space author writing a child Space, I want to edit parent text that appears exactly once, failing when it appears zero or several times, so that I can meet an unplanned need without waiting for a bakefile release and a parent change breaks loudly at my call.~~ Dropped 2026-11-26 (ticket 16): fixed text is no part of a template's contract; ask the template's owner for a template hook or an editable block, and detach the file meanwhile.
78. As a Space author, I want a parent template without template hooks to stay changeable through block defaults, so that template hooks are optional.
79. As a Space author, I want every mistake in a child's change (an unknown template hook or block, a block name the template already has) to fail at my own call with the template key in the message, so that I find it in my Space's code.
80. As a Space author, I want a child's insert switched off through a setting the child offers, so that a repo can opt out without removing content by name.
81. As a Space author, I want the engine to read editable block and bakefile value names from the template text, so that I write each name once.
82. As a Space author, I want a test failure when a template's editable block names change, accepted by regenerating the expected files, so that a rename that would drop every repo's edits to that block shows up in review.
83. As a Space author, I want every combination my Space classes produce rendered and checked by `TemplateSuite`, so that a child's inserts are tested like a parent's template.
84. As a Space author, I want Python modules that hold template strings allowed next to template files in `managed/`, so that `TemplateSuite` does not flag them as templates no Space writes.
85. As a repo maintainer, I want to detach a managed file in my Bakebook, keeping the file as it is, so that I can own text outside the editable blocks (a fix that cannot wait, a README that has diverged) without bake overwriting, checking or deleting it.
86. As a repo maintainer, I want to re-attach a detached file by removing `.detach()`, resuming as before when its fixed text still matches and through `--force` otherwise, so that detaching is reversible.
87. As a repo maintainer, I want a file no Space produces any more kept, with a note, when I changed it since bake last wrote it, so that dropping a file never deletes hand edits.
88. As a bakefile maintainer, I want temporary `bake -b demo step<N>` commands that walk the managed file lifecycle on a disposable branch in this repo and check each result, so that the release is accepted on real commands, errors and fixes, not only unit tests.
89. As a repo maintainer with a plain `bakefile.py` and no package of my own, I want to manage my own files from template text, inline or read from a file in my repo, with no package or template name to invent, so that my repo's own files get editable blocks and drift checks too. (Added 2026-11-27.)

## Implementation Decisions

### Engine (new module in bakelib)

- One engine handles template parsing, reading files against templates, rendering, the lock and writing. It is pure Python file I/O: no subprocess, no formatter. Spaces call it; nothing in `bake` imports it (ADR 0004).
- **Template grammar** (from the PoC):
    - `{% editable <name> %}<default>{% endeditable %}`, the closing tag optionally repeating the name. On its own lines it is a block editable block (multi-line, may be empty); inside a line it is inline (single line).
    - `{% editable <name> adopt %}` marks the adopt block, at most one per template.
    - `{{ bakefile.<name> }}` is a bakefile value. A default may contain one.
    - `{% raw %}...{% endraw %}` passes text through.
    - `{% hook <name> %}` on its own line marks a template hook (ADR 0007). It renders to nothing and is not part of the read pattern.
    - Editable block and bakefile value names are read from the template text, never declared (ADR 0007). Load fails on a malformed or near-miss tag, more than one adopt block, two editable blocks or two template hooks with one name, an editable block or bakefile value without fixed text on both sides, a bakefile value the Bakebook does not give or gives as something other than text, or an unsupported file type. Lenient parsing is rejected (ADR 0006).
    - Rendered files contain no tags. Visible `(editable)` markers are fixed text the template author writes.
- **Read**: the template compiles into one pattern of fixed text and captures (block captures take whole lines, inline captures stay within a line; bakefile values match anything). A matching file yields each editable block's content. On no match, report the first fixed line out of place: `expected '<line>', but line N is '<text>'`.
- **No formatter.** Bake never runs one. Templates are authored in the shared oxfmt style (from `BaseSpace`'s managed `oxfmt.config.ts`), so lint's oxfmt and editors leave them unchanged. A multi-line bakefile value sits alone on its line; its hook returns it at column 0 in the shared style and bake indents it to the marker's column. A repo that formats managed files differently sees drift; per-repo style is not supported (ADR 0006, "No formatter in bake").
- **Normalisation**: before reading and hashing, strip a UTF-8 BOM, convert CRLF to LF and add a missing final newline. Writes are LF, no BOM, final newline. A file whose normalised content equals what bake would write is not rewritten.
- **Header**: line 1, fixed text `managed by bakefile; edit only the parts marked "editable"`, in the file type's comment syntax from a fixed table:
    - `# ` for `.yaml`, `.yml`, `.toml`, `.py`, `.sh` and ignore files (`.gitignore`, `.*ignore`)
    - `// ` for `.ts`, `.js`, `.mjs`, `.cjs`, `.json5`, `.jsonc`
    - `<!-- ... -->` for `.md`
    - Plain `.json` and any other type fail at template load. No shebang support yet.
- **`bake.lock`** (ADR 0006): TOML at the project root, top-level `version` and `revision`, then `[managed-content."<path>"]` per file with `template` (`<package>:<name>` as declared, or `repo:<path>` for a repo's own template; amended 2026-11-27, it was `<distribution>:<name>`), `hash` (`sha256:<64 hex>` of the normalised bytes, header included) and `editable.<name>` for each editable block whose content differs from the template default (compared as normalised text). No stored base, no versions, no bakefile values. Shape from the PoC:

    ```toml
    version = 1
    revision = 1
    [managed-content.".github/workflows/ci.yml"]
    template = "bakelib.space:ci.yml"
    hash = "sha256:<64 hex>"
    editable.additional = "  publish:\n    needs: [zerv-versioning, test]\n ..."
    ```

- **Lock**: for each managed file that reads under its current template, record its editable blocks and hash. A file that does not read keeps its existing entry. A lock that does not parse exits 2 with the `mc lock` hint.
- **Sync**: lock first, then for each managed file render the current template with editable blocks taken from the file when it reads, else from the lock when the hash matches. Hash mismatch with a non-reading file exits 2 (hint: reinstall the outgoing template's package, then `mc lock`; or `mc sync --force`. Amended 2026-11-27: for a repo's own template the hint says to restore the previous template in `bakefile.py`). Headerless file at a managed path: taken over with a note when its content equals the rendered defaults without the header; else adopt when the template has an adopt block (content moved verbatim into it); else exit 2. A file in the lock with its header missing is an error. Editable blocks carry over by name; a block gone from the template is dropped with a note. Then delete files the lock lists that no Space produces and that still match their locked hash (a changed one is kept with a note and its entry dropped), write all files, and re-read written files into the lock. Any error before writing: nothing written. `--force` renders from the lock (or defaults) and overwrites.
- **Bakefile values**: the template's text names the values it uses, and the Space gives their text in one mapping, `_get_managed_values(fetch)`, which children extend with `super()`. The engine takes that mapping and nothing else: it calls no hook and looks nothing up by name on the Bakebook. Values are always re-rendered, never locked; when the text in the file differs from the value, sync rewrites it with a note, so a hand edit inside one is not kept.
- **Values from the network** (ADR 0006): the engine does not fetch. Each command passes a fetch mode to `_get_managed_values(fetch)`: `lint` and `mc lock` pass `NEVER`, `mc sync` passes `WHEN_NEEDED`, and `mc sync --refresh` passes `REFRESH`. The code that builds such a value reads the committed file as its cache and fetches only when the mode allows it and the committed text is no longer valid. Where it may not fetch, it gives a one-line "not fetched yet" text, so `lint` reports drift and nothing is written. A failed fetch exits 2 with nothing written.
- **Detached files**: `ManagedFile.detach()` returns a copy with `detached` set. Sync, lock and check skip a detached path: its template is not loaded, nothing is written, compared or deleted, and its lock entry is dropped with a one-line note when the entry goes, silent after that. A detached path with no file gets nothing. Removing `.detach()` makes the file managed again: header and fixed text matching means it reads and locks; otherwise exit 2 with the `--force` hint (ADR 0006).
- **Exit codes**: 0 clean, 1 drift, 2 error.

### Spaces

- **Toggle**: `bake_manage_content: bool = False` on `BaseSpace`, settable in `bakefile.py` or by `BAKE_MANAGE_CONTENT=true`. Off: no write, no drift check, no lock, no output; `mc sync` and `mc lock` exit nonzero with a hint on how to turn it on.
- **Hooks on `BaseSpace`**, composed with `super()` like `_get_mise_tools`:
    - managed files: a mapping from project path to a managed file declaration (package anchor and template name, or template text given as a string through `ManagedFile.from_text`, with a package and name or, for a repo's own template, with neither; the Space gives bakefile values' text in one mapping; amended 2026-11-27). A template file lives at `<package>/managed/<name>` and is read through `importlib.resources`; files are the norm for a parent template, strings suit a child's small inserts. The template key is `<package>:<name>` as declared, or `repo:<path>` (amended 2026-11-27, it was `<distribution>:<name>`). The most-derived Space on the MRO wins a path.
- **Child Spaces change a parent template** (ADR 0007) by taking the declaration from `super()` and returning a changed copy, so changes apply in MRO order. The declaration offers two methods, each returning a new declaration:
    - `insert(hook, text)`: places the text just above the template hook's marker, so a later insert at the same hook lands after this one. Inserted text is indented relative to the template hook's column, as a bakefile value is. Fails when the template hook is unknown or the text adds an editable block the template already has.
    - `set_default(block, text)`: replaces an editable block's default. An inline block takes one line. Fails when the block is unknown or holds a template hook.

    Errors raise at the child's call with the template key in the message, and a command reports them as exit 2 with nothing written. Shape from the prototype:

    ```python
    class JobChild(ParentSpace):
        def _get_managed_files(self) -> dict[str, ManagedFile]:
            files = super()._get_managed_files()
            files[SECURITY] = files[SECURITY].insert("extra_jobs", CHILD_JOB)
            return files
    ```

- **Commands**: a `managed-content` command group with a hidden `mc` alias: `lock`, `sync` (`--force`, `--dry-run`, `--refresh`). `--dry-run` may fetch, so it shows the real change.
- **Ordering**:
    - `setup-dev`: lock and sync at the start of `BaseSpace`'s project step, which every Space runs first through `super()`. It comes before the clean, because the clean removes `.venv`, which is the venv bake runs from (templates and package metadata included) when a project has bakefile in its own dependencies. A sync that fails then also stops `setup-dev` with the environment intact.
    - `update`: lock in-process before any upgrade; after tools and dependencies are upgraded, run sync as a fresh `bake mc sync --refresh` subprocess so the newly installed templates are used and values from the network come from their latest upstream (ADR 0006: lock with the outgoing bake, write with the new one).
    - `lint`: in `BaseSpace`'s fast step, before oxfmt or any other formatter: relock, then the drift check (exit 1 on drift with a hint to run `mc sync`), only with the toggle on.
- **Content**:
    - `BaseSpace` `oxfmt.config.ts`: the shared style as fixed text, content as this repo's own, plus an editable block inside `ignorePatterns`, empty by default (stable under oxfmt). The template source is named `oxfmt-config.ts`: a template named `oxfmt.config.ts` is read by oxfmt as a nested config for its folder.
    - `BaseSpace` `.gitignore`: header, then the generated stack section (a value from the network: `_get_gitignore_templates()` lists [github/gitignore](https://github.com/github/gitignore) template paths, `BaseSpace` `Global/macOS`, `Global/Windows`, `Global/VisualStudioCode`, plus `Python` in `PythonSpace` and `Rust` in `RustSpace`; nothing ships in the package: sync fetches the templates from github/gitignore (raw files at one commit: `main`'s SHA from `git ls-remote` on the first sync, the section's own commit when the list changed or a hand edit is repaired, as long as its commit line can still be read; a template that answers 404 at that commit exits 2 saying to run `bake mc sync --refresh`) only when the file has no section, the list changed or the section was edited by hand, and `mc sync --refresh` (so `bake update`) fetches `main` again; the committed section is the cache, read only from above the editable block, sorted by path after a `# Created from github/gitignore@<sha>` line and a `# Templates: <paths>` line and a line saying to override `_get_gitignore_templates()` in `bakefile.py`, and before an end line holding a digest of the whole section, those start lines included, so `lint` checks it with no network and reports a changed list or a hand edit anywhere in it as drift; a failed fetch exits 2 with nothing written), then the Space lines under `# Lines from bakefile.py; to change them, override _get_gitignore_lines()` (a bakefile value: `_get_gitignore_lines()` returns a set, `BaseSpace` `.env*`, `*.local.md`, `*.local.toml`, `.claude/settings.local.json`, `.claude/worktrees/`, `.playwright-mcp/`, `.scratch`, `**/.ssh/id_*`, `**/.ssh/*_id_*`, `**/.ssh/known_hosts`, plus `rust-project.json` (rust-analyzer) in `RustSpace`; written sorted with `!` lines last), then one editable block, `repo`, under `# (editable)`, last so its rules win: it adopts an existing hand `.gitignore` verbatim and takes lines other tools append. A blank line separates the three parts.
    - `GitHubActionsTools` `.github/renovate.json5`: `$schema` and `extends: ["config:recommended"]` as fixed text, plus an editable block for repo rules before the closing brace.
    - `ZervGitHubActionsTools`, a new child Space of `GitHubActionsTools` for zerv versioning in GitHub Actions: `.releaserc.mjs` as a whole fixed file (content as this repo's own), and `.github/workflows/semantic-pull-request.yml` (content as this repo's own) with `name`, `on`, `permissions`, the job and its steps as fixed text and the pin and `runs-on` as inline editable blocks, because Renovate and `actions-up` bump the pinned `amannn/action-semantic-pull-request` SHA in place and a bump in fixed text would be drift.
    - Workflow templates, content as this repo's own (the survey of the local personal repos found these shared). Fixed text is the workflow's `name`, `on`, `permissions`, job headers and steps; each pin and `runs-on` is an inline editable block, anything else that varies between repos is an editable block, and each file ends with an editable block for repo-only jobs:
        - `GitHubActionsTools` security workflow: trivy and gitleaks jobs. Its triggers, schedule included, are one `events` editable block; each `runs-on` and each pin is an inline editable block; the trivy inputs end in an editable block holding the `trivy_inputs` template hook, and the `extra_jobs` template hook sits before the trailing editable block for repo-only jobs. The template hooks serve company Spaces downstream; no bakelib Space inserts into the workflow, and the docs show the cargo audit job a Rust repo adds in the trailing editable block.
        - Python workflow templates in `bakelib.space`: pre-commit, publish and test (OS matrix and Python versions editable). They ship unused: `PythonSpace` and `PythonLibSpace` know nothing of GitHub Actions and write none of them; a later Space, outside this spec, will, and until then a repo declares them in its own `_get_managed_files()`, as this repo's `bakefile.py` does (amended 2026-11-26: `PythonSpace` wrote pre-commit and `PythonLibSpace` publish; the test template was already unused).
        - `ZervGitHubActionsTools` ci and cd workflows: triggers and permissions fixed, the zerv versioning and release jobs in an editable block, and an empty editable block the repo fills with its jobs by hand. No Space adds jobs: `BaseSpace` and the Python Spaces know nothing of GitHub Actions, and a later Space, outside this spec, will own the jobs (amended 2026-11-26; they were bakefile values `ci_jobs` and `cd_jobs` that `PythonLibSpace` filled).
    - `FnoxSpace` keeps its existing `.gitignore` append for the fnox cache, which keeps working while the toggle is off; with the toggle on, the line is already among `BaseSpace`'s Space lines, so the append is a no-op.
- **This repo**:
    - Exclude the `managed/` template directories from oxfmt (`"**/managed/"` in the `ignorePatterns` editable block of `oxfmt.config.ts`) so `bake lint` does not reformat template sources.
    - Turn managed content on (in the first ticket after bakefile values) and move each managed file over as its template ships: `--dry-run` first, `--force` only where a file differs, diffs reviewed, `bake.lock` committed. A second sync, `lint`, `setup-dev` and `update` change nothing, and CI passes.
    - This repo's hand `.gitignore` is adopted verbatim, toptal section included (no migration). After adoption, delete the toptal section from the `repo` block by hand and add any template still needed through `_get_gitignore_templates()` in `bakefile.py`.
    - The `bake update` step bumps template pins by pattern (ADR 0007): it finds every `owner/repo@<sha> # <tag>` in template files, `.yml` and `.py`, including pins inside an inline editable block, writes the unique pins as steps of a throwaway workflow, runs `actions-up` on that workflow, and writes the bumped pins back. Templates never pass through `actions-up`, so the marker masking goes away.
    - `.prettierrc.json` and other pre-lock leftovers in downstream repos are removed by hand once, not by bake.
- **v1 is dropped**: build from `main`, no migration from v1 headers or blocks. The ignored v1 leftover directories are already deleted.

## Testing Decisions

- A good test drives a Space command in a temporary project and asserts only on what a user sees: files on disk, `bake.lock`, the exit code and the message. No assertions on engine internals.
- **One seam: Space commands.** `setup_dev`, `update`, `lint` and the `managed-content` commands on Space subclasses, run in a temporary project directory with the mocked context, as `tests/unit/bakelib/space/` already does (prior art: `test_base_space.py`, `test_github.py`, `test_fnox_space.py`). Engine edge cases go through this seam too, using test Spaces in a small test package that ships fixture templates under `managed/`. Cover:
    - toggle on, off and by env var; `mc sync` hint when off
    - hook composition with `super()`, diamonds, most-derived wins, whole-file override
    - each PoC scenario that still applies: fresh (shared style, lock without editable entries, second sync unchanged); upgrade keeping a Renovate bump and a hand edit; bad hand content (exit 2, nothing written); drift in fixed text (exit 2, `--force` removes it); edit inside an editable block; emptied editable block stays empty while untouched blocks take the new default; Renovate bump then `setup-dev`, `lint` or `update`; hand upgrade with current lock and with an unlocked edit (exit 2, `--force`); markdown and `.gitignore` adoption; headerless structured file (exit 2); dropped file deleted and a later hand file left alone; dropped file changed since locked kept with a note; detached file left alone by sync, lint and update (fixed-text edit kept, lock entry dropped with a note once), re-attached cleanly and through `--force`, detached path with no file; hook-backed bakefile value rewritten and hand edit reverted with a note; headerless file equal to the rendered defaults taken over without `--force`; an editable block whose default is a hook value follows the Spaces until edited
    - template load errors (undeclared name, malformed and near-miss tags, missing block, two adopt blocks, adjacent captures, unsupported file type, `.json`)
    - lock rebuild from files, unparsable lock (exit 2), missing header on a locked file
    - CRLF, BOM and missing final newline: no drift, no rewrite
    - `--dry-run` writes nothing; any error writes nothing
    - drift in `lint`, and drift checked before oxfmt runs
    - fetch modes: `lint` and `mc lock` pass `NEVER`, sync `WHEN_NEEDED`, `--refresh` `REFRESH`; a value the Bakebook does not give exits 2
    - each first-release Space's content
- **One exception to the seam**: the functions that talk to github/gitignore (`git ls-remote` and the raw file download) are tested directly with `subprocess.run` and `urlopen` patched, because every Space-level test runs with a stand-in upstream.
- **Child Spaces in the same seam**: test Spaces that insert at a template hook and replace a default, run through the Space commands: MRO order of inserts, a string template, editable blocks inside an insert locked and kept across a repo edit and a Renovate bump, a child's switch turning its insert off, and each mistake (unknown template hook or block, a repeated block name, a new default on a block holding a template hook) exiting 2 with nothing written.
- **Template test in the same seam**: one parametrised test over every managed file a bakelib Space declares, with the toggle on: sync into an empty project, `oxfmt --check` the written files with the shared config, check for no trailing whitespace and no whitespace-only lines, read them back to exactly the defaults, and a second sync changes nothing. The `.gitignore` stack section renders from a stand-in upstream the test passes, never from the network. Linting rendered output and sorter-friendly rules wait for the first CI or TOML template. `TemplateSuite` covers every concrete Space class, so child combinations render as Spaces do; it also compares each managed file's editable block names with an expected snapshot (regenerated with `BAKE_UPDATE_EXPECTED=1`), and skips Python modules in `managed/` when it looks for templates no Space writes.
- **Dogfood**: this repo's real CI runs every managed workflow; no linter for rendered workflows yet.
- **End to end**: temporary `bake -b demo step<N>` commands in `scripts/demo/` walk the managed file lifecycle with real `bake` commands on a disposable branch of this repo, checking each step's exit code and message, and return to the branch they started from (a worktree included). Normal use comes first and can run early; the error and escape-hatch steps and the final run of them all come last, after every other ticket. A mismatch fixes the steps or files a bug. Removed with `scripts/demo/` once reviewed (`9ad4aa4`); `e2e-runbook.md` records the run and how to restore it.
- **Pin bump**: the pin bump function is tested with the `actions-up` subprocess patched, asserting on the rewritten files: pins in `.yml` and `.py` bumped, tags and editable tags kept, all other text untouched. Prior art: the masking tests it replaces under `tests/unit/scripts/`.
- **Packaging**: one integration test that builds the wheel and resolves every declared template through `importlib.resources`. No prior art in the repo; it goes with the slow tests in `tests/integration/`.

## Out of Scope

- Formatting managed files into a per-repo style, and formatter discovery.
- A runtime check for broken structured files, such as duplicate keys a hand edit puts into an editable block. Template tests only; revisit when a YAML template with block-level editable blocks (a CI workflow) ships.
- Plain `.json` managed files and shebang files.
- A Space owning agent docs (`docs/agents/*`, the `## Agent skills` section in `AGENTS.md`).
- Company content (PR template, company Renovate and pre-commit config, and the work repos' workflows such as their security, Renovate and PR-unlock callers), added later in company Spaces (in data-kit) through the same hooks.
- Pinned refs: reading a pinned `uses:` in fixed text as a wildcard so pins could leave editable blocks. Start relaxed and add it when a need shows.
- Linting rendered workflows (actionlint) in the template test; add it if a broken workflow template ever ships.
- Workflows found in one or two repos (deploy, terraform, e2e and similar) and the PR-unlock workflow.
- A ruff base config (later, as a managed file; the repo's `pyproject.toml` must also `extend` it).
- Conformance checks: read-only `lint` checks that a file a Space does not own contains a line (for example the ruff `extend`, or a workflow calling the shared semantic-release workflow that `.releaserc.mjs` needs). Dropped 2026-11-24: a survey of the 16 local bakelib repos found no gap to catch today, and every other candidate fit a managed file, an existing tool or runtime enforcement better. Revisit with the ruff base config.
- Changing how mise tools are managed.
- Migrating v1 headers or blocks.
- Removing pre-lock leftovers such as `.prettierrc.json` (one-time hand cleanup).
- Detaching through `bake.lock`, a command or a Bakebook field listing paths; detach is set per file in `_get_managed_files()` only.
- Stripping the managed header from a detached file; it stays, and the project removes it by hand if it wants.
- Keeping the end-to-end demo commands after the feature closes; they are deleted with the feature, and the unit tests at the Space-command seam remain the regression net.
- A diff in `mc sync --dry-run`; it lists the paths it would write or delete.

## Further Notes

- A bakefile value never contains a pinned action (`uses: ...@<sha>`): bake re-renders values on every write, so a Renovate bump inside one would be reverted. A Space that adds a job with pinned actions inserts it at a template hook, with each pin in an inline editable block.
- `(editable)` notes name the block and nothing else: no examples, and no facts a child's change can make wrong (a schedule's time zone). A block on its own lines gets `# (editable)` (plus a few words where the block's purpose is not obvious, such as `more trivy-action inputs` or `more jobs below`) on the line above; an inline `runs-on` gets a trailing `# (editable)`; a pin gets `# (editable) pin` on the line above its `uses:`, since the version comment already ends that line.
- The real Renovate round trip (a Renovate PR bumping a pin inside an editable block) is checked after the release, since Renovate runs only on `main`.
- Template-authoring rules for later templates (from the PoC): an editable block and a `bakefile.*` value each need fixed text on both sides, so an empty bakefile value leaves its banner in every repo; hand content goes only in editable blocks; inline editable blocks only in short single-line spots. Formatters that reorder lines (`toml-sort`, `taplo reorder_keys`, isort) need a whole sorted group in one editable block, or an editable block above every fixed table; verified at formatter level only.
- Report-only linters (actionlint, yamllint, markdownlint, zizmor) cause no drift but can flag template output; fixers that rewrite fixed text cause drift. Start templates clean under common rule sets.
- Turning the toggle on in a repo with a hand structured file (such as `oxfmt.config.ts`, `renovate.json5`, `.releaserc.mjs` or a workflow) takes it over when it equals the rendered defaults; otherwise it exits 2 (no adopt block), and the maintainer runs `mc sync --force` once and reviews the diff. A repo that validates PR titles in another workflow file removes that step by hand once, or the check runs twice.
- A repo that needs different fixed text asks the template's owner for a template hook or an editable block, then uses `insert`/`set_default` or edits the block, and detaches the file meanwhile. There is no `edit(old, new)`: it targeted raw template text, which is no part of the template's contract, so it broke whenever the parent reworded its text (ticket 16). Detach for good a file that has diverged, such as several paragraphs of a markdown file.
- The end-to-end demo lived in `scripts/demo/` with one `demo = DemoBakebook()` line in `bakefile.py`, and was removed once reviewed (`9ad4aa4`).
- Delete `history/` (and its exclusions in `pyproject.toml`, `.prettierignore` and `.pre-commit-config.yaml`) once implementation no longer needs it.
