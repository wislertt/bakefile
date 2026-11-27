---
status: accepted, Plugins section partly superseded by ADR-0007, "Header and adoption" section partly superseded by ADR-0009
---

# Managed files with editable blocks, state in `bake.lock`

Managed content takes one form: a managed file, rendered by a Space from a template that has editable blocks (parts the project owns) and `bakefile.*` values (parts bake fills from the Bakebook). A region in an otherwise hand-edited file is a template that is mostly editable blocks. Templates ship in the Space's package at their latest version only, and `bake.lock` at the project root records which managed files bake wrote and the editable blocks the project changed. That lets hand content survive template upgrades without a three-way merge, lets bake delete files it no longer produces, and depends on neither git state nor `uv.lock` (a project may have neither). The header grammar and the lock format end up in every downstream repo, which is why they are recorded here.

## `bake.lock`

TOML, with top-level `version` (the format) and `revision` (uv's meaning), then one table per use case, `[managed-content]` first. Each managed file is a `[managed-content."<path>"]` table with `template` (the template key, see Plugins), `hash` (`sha256:<64 hex>` of the file's bytes after normalising line endings to LF, dropping a UTF-8 BOM and ensuring a final newline, header included, as bake last locked or wrote it, so a CRLF checkout matches a lock written elsewhere) and `editable.<name>` for each changed editable block, as one-line strings exactly as in the file (the lock has no readability goal). It holds no stored base, no template or package versions and no `bakefile.*` values: settings and hooks always win, so a stored copy would only be a second source of truth.

An editable block equal to its template default (compared as text, after line-ending normalisation) is left out, and a missing entry means "take the current default". Untouched defaults, such as a pinned tool version, then follow template upgrades. A block set by hand to exactly the default also follows future defaults; to pin it, change any character. There is no `--keep-defaults` option.

A conflicted, missing or hand-edited lock is fixed by re-running `mc lock`, which rebuilds it from the files whenever they read under the current templates. A lock that does not parse exits 2 with that hint.

## Writes and upgrades

Commands live in the `managed-content` group (hidden alias `mc`). `mc lock` reads editable blocks from the files into the lock. It runs first in every command that writes managed files (`setup-dev`, `update`, `mc sync`), so a stale lock never overwrites a hand edit or a Renovate bump, and `bake lint` includes it, so the pre-commit hook relocks on the next local commit. Renovate bumps only the managed file and has no config for `bake.lock`. CI tolerates a stale lock. Because the lock holds the file's text and a content hash, a reformat alone makes it stale until lint relocks it.

When a file reads under the current template, the file is the source. When it does not (the template changed, or the file was edited outside its editable blocks), the hash decides:

- Hash matches the lock: the lock is current, so bake renders the new template from the lock. This is the upgrade, and also how a template switch at a path is handled.
- Hash differs: there are unlocked edits plus a template change, so bake exits 2 and writes nothing. The hint names the package of the outgoing template to reinstall (no version) before running `mc lock`, or offers `mc sync --force`, which renders from the lock and leaves the dropped edits visible in git diff.

`bake update` locks with the outgoing bake, upgrades bakefile and plugins together, then writes with the new templates (the same ordering as ADR 0002). A hand upgrade is safe whenever the lock was current.

Editable blocks carry over by name. A block whose name is gone from the template is dropped with a note on `sync`, and a renamed block starts from its default; git diff shows the dropped content. There is no rename map.

A file in the lock that no Space produces any more is deleted when it still matches its locked hash; one changed since then is kept with a note and its lock entry dropped, so it becomes a hand file (amended 2026-11-26, it was deleted even with hand content). A restored file is not in the lock, so it stays a hand file.

A project detaches a managed file when it must own text outside the editable blocks, for example a fix that cannot wait for the Space's next release: its own Bakebook returns the file's entry from `_get_managed_files()` with `.detach()`. Bake then neither loads the template, writes, checks nor deletes the file, and drops its lock entry; removing `.detach()` resumes management, through `--force` when the fixed text no longer matches. It is set per file in the hook, not in `bake.lock`, so it shows in code review, and a Bakebook field listing paths was rejected for the same reason the hook is where files are declared. Leftovers from before the lock (such as `.prettierrc.json`) are cleaned up by hand once.

## Header and adoption

ADR 0009 removes adoption: a headerless file now exits 2 for every file type, and only the takeover of a file that already equals the defaults stays. The text below is the decision as first made.

The header is fixed text bake owns and is not stored in the lock: `managed by bakefile; edit only the parts marked "editable"`. It has no template key and no version; bake matches a file to its template by path, through the Bakebook.

A file at a managed path without the header is adopted only when its template marks one editable block as the adopt block (`{% editable <name> adopt %}`, at most one per template), and only in line-based or prose files (`.gitignore`, markdown), where appending the old content inside the block keeps the file valid and equivalent. Adopted content is kept verbatim. Any other headerless file exits 2 with nothing written; `mc sync --force` writes the template with default editable blocks and git diff holds the hand content. A missing header on a file in the lock is an error.

## Plugins

ADR 0007 replaces how child Spaces change a parent template, the `values=` declaration and "never template text" below.

A Space declares a managed file as `ManagedFile(__package__, "<name>")`, an anchor and a name, never template text; the template lives at `<package>/managed/<name>` and is read through `importlib.resources`, so Spaces in other packages (company Spaces such as data-kit) ship their own templates. The template key is `<distribution>:<name>` (for example `bakefile:ci.yml`), stored only in the lock and read only for the hand-upgrade hint and the template switch note (amended 2026-11-27: the key is `<package>:<name>` as declared, or `repo:<path>` for a repo's own template; see the amendment below).

Managed files compose like every hook, `{**super()._get_managed_files(), ...}`, and the most-derived Space on the MRO wins a path, with no collision error. A child changes a parent template in two ways only: a `{{ bakefile.<name> }}` value backed by a hook children extend with `super()`, for a planned extension point, which keeps parent upgrades, or a whole-file override at the same path. A `bakefile.*` value, from a setting or a hook, matches anything when read and is always re-rendered, so a changed value never exits 2 and a hand edit inside one is reverted with a note. A value needs fixed text on both sides. Removing a plugin Space or upgrading a plugin goes through the dropped-file and upgrade paths above.

A managed file declares the names of the `bakefile.*` values its template uses, `values=("ci_jobs",)`, and the Space gives their text in one mapping, `_get_managed_values()`, which children extend with `{**super()._get_managed_values(fetch), ...}`, the way a template engine takes a context. The engine takes only that mapping of text: it calls no hook, looks nothing up on the Bakebook and never touches the network.

## Values fetched from the network

A `bakefile.*` value is a pure function of the Space, with one kind of exception: a value whose text comes from the network. The engine does not know the difference. The command decides whether fetching is allowed and passes that to `_get_managed_values(fetch)` as an argument, never as ambient state: `lint` and `mc lock` pass `Fetch.NEVER`, `mc sync` (and so `setup-dev`) passes `Fetch.WHEN_NEEDED`, and `mc sync --refresh`, which `bake update` runs, passes `Fetch.REFRESH`. The code that builds the value reads the committed file, which is its cache, and fetches only when the mode allows it and the committed text is no longer valid.

So there is no cache directory and nothing about the value in `bake.lock`, and `lint` gives the same answer offline and in CI. Where the committed text is not valid and fetching is not allowed, the value is a one-line "not fetched yet" text, which differs from the file, so `lint` reports drift; `lint` and `mc lock` write no managed file, so that line never reaches one. A failed fetch exits 2 with nothing written.

The first such value is the `.gitignore` stack section. Its templates come from github/gitignore, which has no releases and which no maintained Python package bundles, and shipping all of them would grow the wheel by about 40%. The section's first lines record the upstream commit and the template paths and its last line a digest of the whole section, those lines included, so a changed template list or a hand edit anywhere in it is drift. A changed list or a repaired hand edit is fetched at the section's own commit, as long as its commit line can still be read, so the diff holds only what changed; only the first sync and a refresh resolve `main`. The section is read only from above the editable block, so a copy pasted into that block is never the cache. The section renders `Global/` templates (macOS, Windows, VS Code) into each repo, although github/gitignore suggests a global gitignore for them, so contributors who never set one up are covered.

## No formatter in bake

Bake never runs a formatter: it renders, reads and writes plain text. Templates are written in the shared oxfmt style, which `BaseSpace` owns through its managed `oxfmt.config.ts`, so every repo with managed content formats them as a no-op, in `lint` and in an editor on save. Bake's CI renders every template with defaults and runs `oxfmt --check` on it, which also catches an oxfmt release that changes its output. A hook-backed `bakefile.*` value returns text in that style; bake only indents it to the marker's column. A repo that formats managed files differently (its own oxfmt config or version) sees drift; per-repo style is not supported.

## Ownership and rollout

Content is declared through hooks that child Spaces extend with `super()`, the same way mise tools compose. Bake overwrites its own content and never merges it: a hand edit outside editable blocks is drift. `setup-dev` and `update` write, and `lint` reports drift. The feature is behind a `bake_manage_content` toggle, off by default in beta, and no `bake.lock` is written while it is off.

## Considered Options

- **copier** (three-way merge from a versioned template repo). Rejected: hand edits produce conflict markers or `.rej` files, it refuses a dirty working tree, and Jinja answers instead of a Bakebook's Spaces would decide what kind of project a repo is.
- **projen** (whole files owned by components of a class). Its header, read-only generated files and file manifest confirm this design. Rejected as a dependency: a second task runner and composition layer next to bake, JS-first.
- **A stored base or template history** for a three-way merge. Rejected: the PoC showed the file plus the lock's editable blocks and a hash cover every upgrade case without either.
- **Bake-owned regions**, marked `BEGIN`/`END` inside a hand-edited file (v1's managed blocks). Rejected as a second kind: a template that is mostly editable blocks covers the same case with one parser, one header and one lock entry.
- **Formatting templates into repo style** (the PoC: format the template, the template with defaults and the file in batched formatter calls, with placeholder comments for markers). Rejected: it needs formatter discovery per file type, placeholders that survive every formatter and a deterministic installed formatter in `check`, while a shared formatter config makes the output equal to the template anyway.
- **A retirement list** of dated cleanup steps, each with an expiry a unit test enforces. Rejected: the lock already knows every file bake wrote, so it can delete them; pre-lock leftovers are a one-time hand cleanup.
- **`--keep-defaults`**, storing every editable block. Rejected: untouched defaults then never upgrade, and pinning one is rare.
- **Renovate updating `bake.lock`** through a regex custom manager. Not used: relocking in lint and before every write keeps the lock current without per-repo Renovate config.
- **Adopting structured files by top-level key**. Rejected: a hand `ci.yml` or pre-commit config almost always clashes on its top-level keys, and it needs a parser per format. Appending a YAML file inside an editable block silently produces duplicate keys that formatters and loaders accept.
- **A transform function on `ManagedFile`**, patching a parent template's lines. Rejected: it couples plugins to bakefile's exact template text, so a bakefile release can break every downstream repo, and it can break editable markers. An unplanned need is a request for a new hook-backed `bakefile.*` value.
- **A separate slot marker** (`{{ slot.<name> }}`) for content child Spaces extend. Rejected: it behaves exactly like a `bakefile.*` value (matches anything, always re-rendered, never locked), so a hook-backed value covers it with one marker.
- **Reading `bakefile.*` values as fixed text**. Rejected: a changed setting or hook output then exits 2 whenever the lock is stale, with a hint that does not fit.
- **Looking a `bakefile.*` value up by name on the Bakebook** (the hook `_get_<name>()`, else the setting `<name>`; the first implementation). Rejected: a naming rule tied the template to the code that fills it, and every `_get_*` method became a template value. One mapping of text, `_get_managed_values()`, says what a template can use.
- **A context variable telling the `.gitignore` hook whether it may fetch**, with a hidden `mc sync --refresh-gitignore` option for `bake update` (the first implementation). Rejected: a hook did network I/O depending on state set far from the call, the generic sync command knew about one file, and tests swapped the upstream through a second context variable. The fetch mode is an argument of `_get_managed_values()` and the option is a generic `--refresh`.
- **A fetched value the engine knows by kind**, an object with an offline `kept()` and a network `fetch()` that the engine calls by fetch mode (the second implementation). Rejected: the engine carried fetch modes, an unfetched state and a rule about editable blocks for one value. Nearly every value is plain text, so the engine takes text and the code that needs the network decides for itself.
- **Conformance checks**, read-only `lint` pattern checks on files a Space does not own, run without the toggle. Deferred: the one planned check (a workflow uses the semantic pull request action) fits a managed file better, and a survey of our repos found no gap a check would catch today. Revisit with a shared ruff base config, whose `extend` line lives in a repo-owned `pyproject.toml`.
- **Lenient marker parsing** (Ansible, conda, all-contributors). Rejected: their failure modes are duplicated blocks, silent no-ops and deleted lines. Malformed and near-miss markers are errors and nothing is written.

## Amendment, 2026-11-27: template keys as declared

The template key is `<package>:<name>` exactly as the `ManagedFile` declares it (`bakelib.space:ci.yml`), not `<distribution>:<name>`. The distribution was worked out from install metadata (installed packages, then editable-install source folders), so the same code could write a different key depending on what was installed, and a package inside an editable project took that project's name. A committed file must not depend on the environment. The key is provenance only: lock entries are matched by path, and nothing compares keys. The hand-upgrade hint, the one reader that needs a distribution, now looks it up from the key's package when it prints, as a best effort.

A repo's own template, given as text with no package (`ManagedFile.from_text(text)`), has the key `repo:<path>`, and its hint says to restore the previous template in `bakefile.py`. The template switch note named above was never built.
