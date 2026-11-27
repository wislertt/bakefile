# Migrations

Status: ready-for-agent

## Problem Statement

When a Space stops wanting something it once put in a project, nothing removes it. A Space adds mise tools with `mise use`, but never removes a tool it no longer declares, so switching bakelib's GitHub Actions linting from actionlint to jactionlint would leave `actionlint` in every downstream project's `mise.toml`. Leftovers like this (retired tools, config files no longer read) keep piling up, and today each repo owner has to notice and clean them up by hand, repo by repo. Space authors have no way to ship the cleanup together with the change that causes it.

## Solution

A Space ships a Migration (see `GLOSSARY.md`) with the change that needs it: a one-off step that moves projects off what the Space no longer wants. Migrations run inside the normal lifecycle, with no command of their own:

- `bake lint` fails while any Migration still applies to the project, naming it and how to apply it, so CI and the pre-commit hook catch a repo that skipped `update`.
- `bake setup-dev` applies them first.
- `bake update` applies the incoming version's Migrations after upgrading bakefile.

A Migration decides from the project itself whether it still applies, so nothing is recorded. Each one carries an expiry date that has no effect in downstream repos, but fails the shipping package's own tests once it is past, so the Space author removes it. A project that does not want a Migration removes it by key in its own Bakebook. The design is recorded in ADR 0008.

## User Stories

1. As a Space author, I want to ship a Migration alongside the change that makes it necessary, so that downstream projects are cleaned up without manual steps.
2. As a Space author, I want to declare Migrations through a `_get_migrations()` hook that composes through `super()`, so that it works like the other Space hooks I already know.
3. As a Space author, I want to write each Migration as a small subclass with a check and an apply step, so that any kind of leftover can be cleaned up.
4. As a bakefile maintainer, I want bakelib to ship no built-in Migration types, so that there is no extra public API to keep stable for cases too varied to generalise.
5. As a Space author, I want each Migration to carry an expiry date, so that migration code does not accumulate forever.
6. As a Space author, I want my package's tests to fail once a Migration is past its expiry date, so that I am reminded to remove it.
7. As a company Space author (e.g. data-kit), I want a test helper that asserts my Bakebook has no expired Migrations, so that my package enforces expiry the same way bakefile does.
8. As a Space author, I want a sensible default expiry window (90 days from the release that adds it), so that I do not have to think about it each time.
9. As a developer in a downstream project, I want `bake update` to apply the Migrations of the version it just upgraded to, so that one command brings me fully up to date.
10. As a developer, I want `bake setup-dev` to apply pending Migrations before it installs tools, so that a retired tool is removed before the new one is installed.
11. As a developer, I want `bake setup-dev` to apply Migrations at every `-f` level, so that skipping slow steps never skips a cleanup.
12. As a developer whose bakefile was bumped by Renovate or by hand, I want `bake setup-dev` to apply the new Migrations, so that I am not dependent on running `bake update`.
13. As a developer, I want `bake lint` to fail while a Migration still applies, naming it and telling me how to apply it, so that I do not miss a cleanup.
14. As a CI maintainer, I want the lint check for Migrations to be read-only and offline, so that it gives the same answer in CI and locally.
15. As a developer, I want each Migration's description shown when it is applied, so that I understand what changed in my project.
16. As a developer, I want `--dry-run` to show which Migrations would apply and the exact commands they would run, without changing anything, so that I can preview them.
17. As a developer, I want applying a Migration that no longer applies to do nothing, so that running `setup-dev` or `update` again is always safe.
18. As a developer, I want a failing Migration to stop the command with exit 2, and the next run to pick up where it left off, so that a partial failure never leaves the project in an unknown state.
19. As a developer, I want no extra state file or `bake.lock` entry for Migrations, so that there is nothing to conflict on or go stale.
20. As a developer who does not want a Migration, I want to remove it with a plain `del` in my own Bakebook's `_get_migrations()`, so that the opt-out is ordinary Python, visible in code review, and both lint and the lifecycle stop acting on it.
21. As a developer, I want my opt-out to fail with a clear message once upstream has removed that Migration, so that I delete the dead line instead of carrying it forever.
22. As a developer, I want no new public command to learn, so that Migrations stay invisible until one applies.
23. As a developer, I want Migrations applied in a predictable order (parents before children), so that output is stable between runs.
24. As a developer using jactionlint's Space after the switch, I want `actionlint` removed from my project's mise config automatically, so that I do not run or install two linters.

## Implementation Decisions

- **Term**: Migration, defined in `GLOSSARY.md`, distinct from Adoption (managed content's takeover of a headerless file).
- **`Migration` base class** (bakelib): abstract, with `expires: date`, `description: str`, `check(ctx) -> bool` and `apply(ctx) -> None`. `ctx` is passed at call time, never captured at construction, so `_get_migrations()` only declares data.
- **Contract**: `check` is read-only and offline; it runs for real under `--dry-run`, so any `ctx.run` it makes passes `dry_run=False` (the same as the existing mise list query when adding tools). `apply` makes every side effect through `ctx.run`, or skips any direct file edit when `ctx.dry_run` is set.
- **No built-in subclasses**: every Migration is a subclass its Space writes. Leftovers vary too much to generalise, and each built-in would be public API. An author doing a file edit in `apply` checks `ctx.dry_run` itself.
- **Hook**: `_get_migrations() -> dict[str, Migration]` on `BaseSpace`, empty in the base, extended through `{**super()._get_migrations(), ...}`. Keys are stable kebab-case ids. Order is dict order, parents first; Migrations do not depend on each other.
- **Runner** (on `BaseSpace`): for each Migration whose `check` is true, print its description and call `apply`. A raised error exits 2.
- **`lint`**: the fast lint runs every `check` and fails when one applies, listing each by key and description, with a hint to run `bake setup-dev` (or `bake update`).
- **`setup-dev`**: runs the runner as its first step, before platform tools and tools, regardless of the `-f` level.
- **`update`**: its final fresh-process step becomes a hidden command (working name `post-update`, not shown in help) that applies Migrations and then, when managed content is on, runs the managed sync with refresh. This replaces the direct `mc sync --refresh` call. The fresh process is needed because `update` upgrades bakefile mid-run, so the running process only holds the outgoing version's Migrations. The hidden command is invoked with the same bakefile-selection options `update` already forwards.
- **Expiry**: no runtime effect anywhere. bakelib ships `assert_no_expired_migrations(bakebook)`, which fails listing every Migration whose `expires` is before today. Default window 90 days from the adding release, set by the author.
- **Opt-out**: a project removes the key with `del` in its own `_get_migrations()`. bakelib calls `_get_migrations()` in one place, which catches a `KeyError` and exits 2 with a message naming the key: `_get_migrations()` removes Migration `<key>`, which no longer exists upstream, so delete that line. No traceback is shown. Every command that collects Migrations (`lint`, `setup-dev`, the hidden update step) fails this way, so the dead opt-out surfaces right after the upgrade that removed it, the same rule as ADR 0007's errors at a child's own call.
- **First Migration**: a one-off subclass in `GitHubActionsTools` that removes `actionlint` from the project's mise config (`mise unuse`, checked against the local mise tools the way tool adding reads them), added together with the actionlint to jactionlint switch, expiring 90 days after that release.

## Testing Decisions

- Tests exercise external behaviour through the existing seams only: the Space commands, and the public expiry helper. No direct tests of private runner methods.
- **Seam 1, Space commands with `mock_ctx`**: call `lint()`, `setup_dev()`, `update()` and the hidden command on a test Space that declares Migrations, and assert on the captured `ctx.run` commands, the console output and the exit code. Covers: lint fails only while a check applies; setup-dev applies first at every `-f` level; update runs the hidden command in a fresh process with forwarded options, and that command applies then syncs; dry-run runs checks for real and echoes apply commands without running them; a failing apply exits 2; a Migration removed with `del` is neither checked nor applied; a `del` of a missing key exits 2 with the delete-that-line message and no traceback; order is parents first. The test Space declares test-only Migration subclasses, one running a command and one deleting a file under `tmp_path`.
- **Seam 2, `assert_no_expired_migrations`**: passes for future dates, fails naming every expired Migration.
- **bakefile's own expiry test**: calls the helper on bakelib's Spaces.
- **Prior art**: `TestUpdate`, `TestLint`, `TestSetupDev` and `TestAddMiseTools` in the base Space tests (captured `ctx.run`, dry-run bypass for read-only queries), and the GitHub Actions tools tests for Space-specific tool sets.
- No integration tests: `mise unuse` is mocked the same way `mise use` is today.

## Out of Scope

- The rest of the actionlint to jactionlint switch: jactionlint's profile and config, `--online` in the slow lint, deduplicating with zizmor, and dotfiles dropping zizmor from its own subclass. A separate design after this lands.
- A public `bake migrate` command.
- Recording applied Migrations anywhere (`bake.lock` or a state file).
- Dependencies or ordering constraints between Migrations.
- Runtime warnings or failures based on expiry dates.
- Migrating managed files: managed content already handles dropped and changed managed files (ADR 0006).

## Further Notes

- ADR 0008 (`proposed`) records the decisions and rejected options; mark it `accepted` when this lands.
- A Space only migrates what it added: zizmor comes from dotfiles' own subclass, so bakelib ships no Migration for it.
