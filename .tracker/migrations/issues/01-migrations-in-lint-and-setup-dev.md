# 01: Migrations in lint and setup-dev

Status: ready-for-agent

Blocked by: None (can start immediately)

Spec: `.tracker/migrations/spec.md`. Decision: `docs/adr/0008-migrations-with-expiry.md`.

**What to build:** A Space declares Migrations through a new hook, and they act through the normal lifecycle: `lint` fails while one still applies, and `setup-dev` applies them first. A project opts out of one with a plain `del`, and that opt-out fails clearly once upstream has removed the Migration. bakelib ships the abstract `Migration` and the hook only, no built-in Migration types.

- [ ] Abstract `Migration` in bakelib with `expires: date`, `description: str`, `check(ctx) -> bool` and `apply(ctx) -> None`; `ctx` is passed at call time
- [ ] `_get_migrations() -> dict[str, Migration]` on `BaseSpace`, empty in the base, composed through `super()`; Migrations run in dict order (parents first)
- [ ] bakelib calls `_get_migrations()` in one place; a `KeyError` raised there exits 2 naming the key with a hint that the Migration no longer exists upstream and the line removing it should be deleted, with no traceback
- [ ] Fast `lint` runs every `check` and fails when any applies, listing each by key and description with a hint to run `bake setup-dev` (or `bake update`); offline, and the same with or without `--dry-run`
- [ ] `setup-dev` applies every Migration whose `check` is true as its first step, before platform tools and tools, at every `-f` level, printing each description before applying
- [ ] Under `--dry-run`, `check` runs for real and `apply` is still called, so `ctx.run` echoes its commands without running them
- [ ] An error raised by `apply` exits 2; a rerun picks up the remaining Migrations because `check` decides again
- [ ] A Migration removed with `del` in a child Bakebook is neither checked by `lint` nor applied by `setup-dev`
- [ ] Unit tests through the Space commands with `mock_ctx` and captured `ctx.run` (prior art: `TestLint`, `TestSetupDev`, `TestAddMiseTools`), using test-only Migration subclasses: one that runs a command, one that deletes a file under `tmp_path` and skips the delete under `--dry-run`
- [ ] `src/bake/bakebook/README.md` or the bakelib Space docs explain how to write a Migration, the check/apply contract, dry-run, and the `del` opt-out

## Comments
