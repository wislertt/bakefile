# 10: Apply the new template shape to the shipped templates

Status: resolved

Blocked by: 08, 09

Spec: `.tracker/managed-content/spec.md` (Further Notes on `(editable)` notes). Decision: `docs/adr/0007-child-spaces-extend-parent-templates.md`. Prototype: `demo/inheritance/managed/security.yml` on the local branch `archive/managed-content-demo`.

**What to build:** The templates bakelib ships read the way the prototype settled on, and the security workflow offers template hooks for company Spaces downstream. Notes are short, every pin and `runs-on` is its own inline editable block, and a repo maintainer sees at a glance what they may edit.

- [x] `(editable)` notes name the block and nothing else: no examples, no facts a child's change can make wrong; a block on its own lines gets `# (editable)` on the line above (plus a few words only where the purpose is not obvious, such as `more trivy-action inputs` or `more jobs below`); an inline `runs-on` gets a trailing `# (editable)`; a pin gets `# (editable) pin` on the line above its `uses:`
- [x] Security workflow: triggers and schedule in one `events` block; each `runs-on` and each pin an inline editable block; the trivy inputs end in an editable block holding the `trivy_inputs` template hook; the `extra_jobs` template hook sits before the trailing editable block for repo-only jobs
- [x] Pre-commit, publish and semantic-pull-request workflows: pins and `runs-on` as inline editable blocks where whole steps blocks are editable today, with the same notes; `renovate.json5` and the other templates get the same notes
- [x] Block names are chosen once here, since renaming them later drops repos' edits; the block-name snapshots and expected files are regenerated, and ticket 08's bump still finds every pin
- [ ] This repo resyncs: diffs reviewed, repo content kept, `bake.lock` committed; a second `mc sync` and `bake lint` change nothing; CI passes
- [x] The docs' cargo audit example matches the new security workflow

## Comments

- 2026-11-26: Block names. Rule: `<job>_runs_on`, `<job>_checkout`, `<job>_action` for the job's own main action, `<job>_<tool>` for helper actions, with the job name in snake case.
    - `security.yml`: `events`, `trivy_runs_on`, `trivy_checkout`, `trivy_action`, `trivy_with` (holds hook `trivy_inputs`), `gitleaks_runs_on`, `gitleaks_checkout`, `gitleaks_action`, `jobs`; hook `extra_jobs` above `jobs`. These are the prototype's names; its `gitleaks_env` block and `{{ bakefile.runs_on }}` value were not taken (not asked for; a block can be added later without dropping edits).
    - `pre-commit.yml`: `pre_commit_runs_on`, `pre_commit_checkout`, `pre_commit_mise`, `pre_commit_cache`, `jobs`.
    - `publish.yml`: `publish_runs_on`, `publish_checkout`, `publish_mise`, `jobs`.
    - `semantic-pull-request.yml`: `semantic_pull_request_runs_on`, `semantic_pull_request_action`.
    - Unchanged: `repo` (gitignore), `ignore` (oxfmt), `rules` (renovate).
- 2026-11-26: Notes: trailing blocks are `# (editable) more jobs below`; gitignore, renovate and oxfmt blocks are a bare `(editable)` (was `below this line` / `ignore patterns`). `gitignore.py`'s `_EDITABLE` marker follows, since the stack section is read from above it. The security cron line lost its `# run once a day at 4 AM` comment (a fact a child's `set_default` could make wrong). The semantic-pull-request step now reads `name:` then `uses:`, so the pin note sits above `uses:`.
- 2026-11-26: Steps are now fixed text in pre-commit, publish and semantic-pull-request (only pins and `runs-on` stay editable), per the ticket. A repo that needs another step there now needs `--force`, an `edit()` in its Bakebook, or a detach. Worth a human look: a trailing `more steps` block would keep that relaxed, but it was not asked for.
- 2026-11-26: Tests: `TestWorkflows` checks the new security shape, a company Space inserting at `trivy_inputs` and `extra_jobs` (insert edited and locked as `trivy_with`), and that every pin and `runs-on` in each shipped workflow carries its note; `test_every_pin_in_the_shipped_templates_is_bumped` runs ticket 08's bump over copies of the shipped `.yml` templates.
- 2026-11-26: Resync. Before syncing, the old `.gitignore` marker line was changed by hand to `# (editable)`, so the stack section cache still reads and sync did not refetch github/gitignore at a newer `main`. `mc sync` rewrote renovate, oxfmt and the four workflows; repo content (`.gitignore` `repo`, oxfmt `ignore`) was kept. A second `mc sync` and `bake lint` change nothing; `bake test` passes. CI cannot be checked locally, so that box stays unticked.
- 2026-11-26: Follow-up: each pre-commit, publish and semantic-pull-request job's steps now end in an empty trailing block under `# (editable) more steps below`, so a repo adds steps without `--force`, `edit()` or a detach: `pre_commit_steps`, `publish_steps`, `semantic_pull_request_steps`.
