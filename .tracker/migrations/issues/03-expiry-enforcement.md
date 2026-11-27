# 03: Expiry enforcement

Status: resolved

Blocked by: 01

Spec: `.tracker/migrations/spec.md`. Decision: `docs/adr/0008-migrations-with-expiry.md`.

**What to build:** A Migration's expiry date has no effect in downstream repos, but the package that ships it fails its own tests once it is past, so the author removes it. bakelib offers this as a test helper so company Spaces enforce expiry the same way bakefile does.

- [x] `assert_no_expired_migrations(bakebook)` in bakelib: passes when every Migration's `expires` is today or later, and fails naming every expired one by key, description and date
- [x] No runtime effect: no command reads `expires`
- [x] bakefile's own unit test calls the helper on every bakelib Space, so a future Migration added past its date fails bakefile's CI
- [x] Unit tests for the helper with future, today and past dates, including several expired at once
- [x] The Migration docs from ticket 01 mention the helper and the default 90-day window

## Comments

`assert_no_expired_migrations` lives in `bakelib/space/migration.py`, exported as `from bakelib import assert_no_expired_migrations`. It reads Migrations through the same collection point as lint and setup-dev (`BaseSpace._collect_migrations()`, split out of `_pending_migrations()`), so a dead `del` exits 2 with the delete-that-line message there too. bakefile's own test (`tests/unit/bakelib/space/test_migration_expiry.py`) finds every `BaseSpace` subclass in the `bakelib` package by walking its modules, and builds each without construction (abstract methods stubbed), as `TemplateSuite` does, since some Spaces validate project fields.
