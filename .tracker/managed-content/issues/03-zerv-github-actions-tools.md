# 03: ZervGitHubActionsTools

Status: resolved

Blocked by: 01, 02

Spec: `.tracker/managed-content/spec.md`. Decision: `docs/adr/0006-managed-files-and-bake-lock.md`.

**What to build:** `ZervGitHubActionsTools`, a new child Space of `GitHubActionsTools` for repos that version with zerv in GitHub Actions, manages `.releaserc.mjs` and the semantic pull request workflow.

- [x] `ZervGitHubActionsTools` ships `.releaserc.mjs` as a whole fixed file (content as this repo's own)
- [x] `ZervGitHubActionsTools` ships `.github/workflows/semantic-pull-request.yml` (content as this repo's own): `name`, `on`, `permissions` and the job fixed, the steps in an editable block so Renovate and `actions-up` bumps of the pinned action survive
- [x] Tests cover both files' content and a pin bump in the workflow's editable block surviving `mc sync` and `lint`
- [x] Exported from `bakelib` like the other Spaces, listed in the Spaces docs
- [x] This repo's `bakefile.py` uses `ZervGitHubActionsTools`
- [x] This repo's `bake update` bumps pinned actions in the workflow templates (`actions-up` on a copy with the marker lines commented out), since Renovate and `actions-up` only scan `.github/`

## Comments

- 2026-11-24: the semantic pull request requirement moved from a conformance check to a managed workflow (bake can own the whole file). Conformance checks are dropped from this release: a survey of the 16 local bakelib repos found no gap a check would catch today (see the spec's Out of Scope).
