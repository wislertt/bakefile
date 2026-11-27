---
status: accepted
---

# Migrations: stateless checks in the lifecycle, expiry enforced by tests

When a Space stops wanting something it once put in a project (a tool it added with `mise use`, a config file it no longer reads), nothing removes it: `_add_mise_tools` only adds, and managed content only cleans up the managed files in `bake.lock`. Switching actionlint to jactionlint would leave `actionlint` in every project's `mise.toml`. A Space now ships a Migration for that: a one-off step kept for a limited time to move projects off the old thing.

## Shape

A Space returns its Migrations from `_get_migrations() -> dict[str, Migration]`, composed through `super()` like `_get_managed_files()`, so a company Space ships its own and a project drops one with `del migrations["<key>"]`. Once upstream removes that Migration, the `del` raises `KeyError`; bakelib's single call to `_get_migrations()` turns it into exit 2 naming the key and asking to delete the line, so a dead opt-out surfaces at the upgrade that removed it (the same rule as ADR 0007: a child naming something that does not exist fails at its own call). `pop(key, None)` was rejected because it leaves dead opt-outs forever, and a `skip_migrations()` helper as needless API over plain `del`. `Migration` is an abstract base class with `expires: date`, `description: str`, `check(ctx) -> bool` and `apply(ctx) -> None`. bakelib ships no built-in subclasses: every Migration is a small subclass its Space writes, because leftovers vary too much to generalise and each built-in would be public API. Migrations run in dict order (parents first) and do not depend on each other.

`check` is read-only and offline, and runs for real even under `--dry-run` (its `ctx.run` calls pass `dry_run=False`). `apply` makes every side effect through `ctx.run`, or skips any direct file edit when `ctx.dry_run` is set, so `--dry-run` previews the real commands. A failing `apply` exits 2; the next run continues, because `check` decides again from the project.

## No stored state

Nothing records which Migrations ran. `check` reads the project itself (is `actionlint` in `mise.toml`?), so a Migration is idempotent and works without git or a lock entry, for the same reason `bake.lock` holds no second copy of what the files already say (ADR 0006).

## In the lifecycle, no command

There is no public `migrate` command; Migrations are rare and run inside existing commands:

- `lint` runs every `check` and fails when one still applies, naming it and how to apply it, so CI and the pre-commit hook catch a repo that skipped `update`.
- `setup-dev` applies them first, at every `-f` level, so a retired tool is removed before tools are installed.
- `update` upgrades bakefile mid-run, so the process holds the outgoing version's Migrations. Its last step is a hidden `post-update` command run in a fresh process, which applies the incoming Migrations and then runs the managed sync with refresh (replacing the direct `mc sync --refresh` call).

## Expiry

`expires` has no effect at runtime: a downstream repo never breaks because of a date. The shipping package's own unit test fails once a Migration is past its date, which forces its removal; bakelib ships `assert_no_expired_migrations(bakebook)` so company Spaces enforce the same. The default window is 90 days from the release that adds it.

## Considered Options

- **A declarative list such as retired mise tools.** Rejected: it fits the actionlint case only; leftovers take many forms.
- **Callables (`check`/`apply` closures over `self.ctx`).** Rejected: the read-only and dry-run contract would live at each call site, and reusable cases need `ctx` at construction.
- **A "migrations run" list in `bake.lock`.** Rejected: a second source of truth that goes stale when a project is edited by hand.
- **A public `bake migrate` command.** Rejected as surface for something rarely run; the hidden `post-update` exists only because `update` needs the incoming version's code.
- **`update` ending with `setup-dev -ff`.** Rejected: it also cleans and reinstalls pre-commit, which `update` does not do.
- **Expiry by bakefile version, or a runtime warning after the date.** Rejected: a date is simpler to set at release, and runtime effects would break or nag downstream repos for a decision that belongs to the Space author.
