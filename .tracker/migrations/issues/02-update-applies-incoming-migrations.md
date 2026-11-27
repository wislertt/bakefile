# 02: update applies the incoming version's Migrations

Status: ready-for-agent

Blocked by: 01

Spec: `.tracker/migrations/spec.md`. Decision: `docs/adr/0008-migrations-with-expiry.md`.

**What to build:** `bake update` upgrades bakefile mid-run, so the running process only holds the outgoing version's Migrations. Its final step becomes a hidden command run in a fresh process, which loads the upgraded code, applies its Migrations, then does the managed sync. A user still runs only `bake update`; there is no public migrate command.

- [ ] A hidden command (working name `post-update`), not shown in `--help`, that applies Migrations the same way `setup-dev` does, then, when managed content is on, runs the managed sync with refresh
- [ ] `update`'s final step runs that hidden command in a fresh process through the existing bake-command builder, so the bakefile-selection options (`--chdir`, `--global`, `--file-name`, `--book-name`) are forwarded; it replaces the direct `mc sync --refresh` call and runs whether managed content is on or off
- [ ] The managed lock at the start of `update` stays where it is (before the upgrades)
- [ ] `--dry-run` and failure behaviour match ticket 01 (exit 2 on a failing apply)
- [ ] Unit tests through `update()` and the hidden command with `mock_ctx` (prior art: `TestUpdate`): the fresh-process call and its forwarded options, apply-then-sync order, sync skipped when managed content is off

## Comments
