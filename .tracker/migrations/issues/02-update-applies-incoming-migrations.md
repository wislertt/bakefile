# 02: update applies the incoming version's Migrations

Status: resolved

Blocked by: 01

Spec: `.tracker/migrations/spec.md`. Decision: `docs/adr/0008-migrations-with-expiry.md`.

**What to build:** `bake update` upgrades bakefile mid-run, so the running process only holds the outgoing version's Migrations. Its final step becomes a hidden command run in a fresh process, which loads the upgraded code, applies its Migrations, then does the managed sync. A user still runs only `bake update`; there is no public migrate command.

- [x] A hidden command (working name `post-update`), not shown in `--help`, that applies Migrations the same way `setup-dev` does, then, when managed content is on, runs the managed sync with refresh
- [x] `update`'s final step runs that hidden command in a fresh process through the existing bake-command builder, so the bakefile-selection options (`--chdir`, `--global`, `--file-name`, `--book-name`) are forwarded; it replaces the direct `mc sync --refresh` call and runs whether managed content is on or off
- [x] The managed lock at the start of `update` stays where it is (before the upgrades)
- [x] `--dry-run` and failure behaviour match ticket 01 (exit 2 on a failing apply)
- [x] Unit tests through `update()` and the hidden command with `mock_ctx` (prior art: `TestUpdate`): the fresh-process call and its forwarded options, apply-then-sync order, sync skipped when managed content is off

## Comments

The hidden command is `post-update` (`BaseSpace.post_update`), registered with `@command(name="post-update", hidden=True)`, so it is callable as `bake post-update` but absent from `--help`. `update` always ends with `ctx.run(self._bake_command("post-update"))`; under `--dry-run` that command is only echoed, the same as the other `update` steps. A non-zero exit from the child (2 from a failing apply or a dead opt-out) ends `update` with that code through `ctx.run`. Docs: one sentence in the Migrations section of `docs/site/bakelib/spaces.mdx`, and the `bake update` lines in `docs/site/bakelib/managed-content.mdx`. Tests: `TestUpdateMigrations` and the `post_update` case of `TestDeadOptOut` in `tests/unit/bakelib/space/test_migration.py`; `TestUpdate` in `test_managed_content.py` now expects `post-update` last and checks its sync refreshes.

- 2026-11-27: Review decision: `bake update --dry-run` stays as is, echoing `bake post-update` without previewing any Migration. A dry run upgrades nothing, so the incoming version's Migrations are not installed to preview. The Migrations section of `docs/site/bakelib/spaces.mdx` says so and points to `bake --dry-run post-update` or `bake --dry-run setup-dev` to preview the Migrations that apply now.
