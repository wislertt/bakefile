# 03: Expiry enforcement

Status: ready-for-agent

Blocked by: 01

Spec: `.tracker/migrations/spec.md`. Decision: `docs/adr/0008-migrations-with-expiry.md`.

**What to build:** A Migration's expiry date has no effect in downstream repos, but the package that ships it fails its own tests once it is past, so the author removes it. bakelib offers this as a test helper so company Spaces enforce expiry the same way bakefile does.

- [ ] `assert_no_expired_migrations(bakebook)` in bakelib: passes when every Migration's `expires` is today or later, and fails naming every expired one by key, description and date
- [ ] No runtime effect: no command reads `expires`
- [ ] bakefile's own unit test calls the helper on every bakelib Space, so a future Migration added past its date fails bakefile's CI
- [ ] Unit tests for the helper with future, today and past dates, including several expired at once
- [ ] The Migration docs from ticket 01 mention the helper and the default 90-day window

## Comments
