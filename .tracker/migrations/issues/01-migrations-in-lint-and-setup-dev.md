# 01: Migrations in lint and setup-dev

Status: resolved

Blocked by: None (can start immediately)

Spec: `.tracker/migrations/spec.md`. Decision: `docs/adr/0008-migrations-with-expiry.md`.

**What to build:** A Space declares Migrations through a new hook, and they act through the normal lifecycle: `lint` fails while one still applies, and `setup-dev` applies them first. A project opts out of one with a plain `del`, and that opt-out fails clearly once upstream has removed the Migration. bakelib ships the abstract `Migration` and the hook only, no built-in Migration types.

- [x] Abstract `Migration` in bakelib with `expires: date`, `description: str`, `check(ctx) -> bool` and `apply(ctx) -> None`; `ctx` is passed at call time
- [x] `_get_migrations() -> dict[str, Migration]` on `BaseSpace`, empty in the base, composed through `super()`; Migrations run in dict order (parents first)
- [x] bakelib calls `_get_migrations()` in one place; a `KeyError` raised there exits 2 naming the key with a hint that the Migration no longer exists upstream and the line removing it should be deleted, with no traceback
- [x] Fast `lint` runs every `check` and fails when any applies, listing each by key and description with a hint to run `bake setup-dev` (or `bake update`); offline, and the same with or without `--dry-run`
- [x] `setup-dev` applies every Migration whose `check` is true as its first step, before platform tools and tools, at every `-f` level, printing each description before applying
- [x] Under `--dry-run`, `check` runs for real and `apply` is still called, so `ctx.run` echoes its commands without running them
- [x] An error raised by `apply` exits 2; a rerun picks up the remaining Migrations because `check` decides again
- [x] A Migration removed with `del` in a child Bakebook is neither checked by `lint` nor applied by `setup-dev`
- [x] Unit tests through the Space commands with `mock_ctx` and captured `ctx.run` (prior art: `TestLint`, `TestSetupDev`, `TestAddMiseTools`), using test-only Migration subclasses: one that runs a command, one that deletes a file under `tmp_path` and skips the delete under `--dry-run`
- [x] `src/bake/bakebook/README.md` or the bakelib Space docs explain how to write a Migration, the check/apply contract, dry-run, and the `del` opt-out

## Comments

`Migration` lives in `src/bakelib/space/migration.py`, exported as `bakelib.Migration` (and `bakelib.space.Migration`). `expires` and `description` are class attributes a subclass sets. `BaseSpace._pending_migrations()` is the single `_get_migrations()` call; `lint` (start of `_lint_fast`, before managed content and formatters) exits 1 with one `Migration <key> applies: <description>` line per Migration plus "run `bake setup-dev` (or `bake update`) to apply pending Migrations". `setup-dev` prints "Applying migrations" then `<key>: <description>` per Migration; any exception from `apply` exits 2 as "Migration <key> failed: <error>". Docs: new "Migrations" section in `docs/site/bakelib/spaces.mdx`. Tests: `tests/unit/bakelib/space/test_migrations.py`.
