# fnox Integration — Context

Captured 2026-10-09. All decisions and research from the discussion live here.

## What is fnox

Secrets manager CLI by jdx (mise author). Config in `fnox.toml`, values resolved
through providers (1Password, Bitwarden, AWS Secrets Manager, GCP, Azure, Vault,
age, plain env). `fnox exec -- <cmd>` injects secrets as env vars. Per-profile
layering like mise.

Docs: https://fnox.jdx.dev

## fnox's own caches (from docs)

| Cache  | Stores                                    | Lifetime                                                      | Refresh                           |
| ------ | ----------------------------------------- | ------------------------------------------------------------- | --------------------------------- |
| Sync   | age-encrypted values in local config file | survives restarts, works offline                              | `fnox sync` re-run                |
| Daemon | resolved values, memory only              | opt-in (`daemon.enabled` / `FNOX_DAEMON=on`), idle timeout 8h | `fnox daemon clear` / `--refresh` |
| Lease  | temporary creds + lease metadata          | until expiry/revocation                                       | auto                              |

Default = **no cache** (plain `fnox get` hits provider every call).

## Decision: how fnox plugs into bakefile

**Final architecture (2026-10-09, after evaluating commit-vs-local):**

```
source of truth   remote vault (1Password / AWS SM / macOS keychain) — team layer
fnox.toml         committed, remote references ONLY, zero secrets in git
FnoxFetchFn       fnox get → resolves reference → real value (fetch origin)
FnoxCache         age-encrypted local file (<project root>/fnox.local.toml),
                  gitignored, never committed — replaces KeyringCache backend
age keys          one keypair, local only, no team key ceremony
```

**Rejected as bakefile's recommended default: age inline-encrypted secrets
committed to git.** Multi-recipient age means collecting teammate pubkeys
upfront, re-encrypting on every join, and rotating every real secret value on
every departure (git history keeps old ciphertext forever, so re-encryption
alone protects nobody). Key ceremony not worth it; remote vault does team
sharing better (accounts, MFA, instant revocation). Local-only age = fine
because no ceremony (single key, single user). Note: still WORKS transparently
if a user picks mode 1 — `FnoxFetchFn` runs `fnox get` regardless of storage
mode, ceremony lives entirely in user config, zero code either way.

Two integration points, both CHOSEN (distinct roles):

1. **`FnoxFetchFn` — fetch origin.** `FetchFn` already designed for pluggable
   origins. Shells `fnox get KEY`; local cache (FnoxCache) sits on top;
   `bake secret refresh` semantics unchanged.

    ```python
    class FnoxFetchFn(FetchFn[str]):
        def __init__(self, key: str, profile: str | None = None) -> None: ...
        def __call__(self) -> str:
            # fnox --no-daemon get KEY ; return stdout.strip()
    ```

    Space opt-in via existing hook:

    ```python
    def get_secret_fetch_fns(self) -> tuple[FetchFn[str], ...]:
        return (FnoxFetchFn("AWS_ACCESS_KEY_ID"), ...)
    ```

    Storage strategy = user's choice via `fnox.toml`, invisible to bakefile
    code. `fnox get` resolves identically for every mode: age inline (committed
    encrypted), remote vault ref, plain default, plus `fnox.local.toml` stack.
    One FetchFn covers all modes.

2. **`FnoxCache` — local cache backend.** Earlier version of this doc rejected
   "fnox as backend" because backends must be fast/local and fnox meant
   network. Objection resolved: the chosen backend stores in a LOCAL
   age-encrypted file only, no network, no daemon. Replaces `KeyringCache`:
   no macOS keychain, no ACL prompts ever, encrypted at rest, portable
   (file copy), `cat`-able (ciphertext).

```sh
fnox --no-daemon -c ~/.cache/bake/secrets.toml get <full-key>
fnox --no-daemon -c ~/.cache/bake/secrets.toml set <full-key> '<json>' --provider age
fnox --no-daemon -c ~/.cache/bake/secrets.toml remove <full-key>
```

## Cache relocation — R1 golden path (2026-10-10, user call after fnox docs research)

Phase 3 dogfood raised multi-repo question (different `key_file` per repo →
first repo's bootstrap wins shared central file, later overrides silently
ignored). User: cache should be repo/space level. Researched fnox docs
(golden-path + sync guides): fnox's own recommendation = per-project
gitignored `fnox.local.toml` (personal sync cache), machine-global or
project-local provider, `--local-file` REJECTS `-c` (explicit paths skip
local cache on later reads).

**Adopted (R1):** cache = `<project root>/fnox.local.toml`, self-contained
`[providers.bake-cache-age]` block (SSOT key_file + recipients; named
`bake-sync-age` until 2026-10-11 — renamed, "sync" had no sync semantics), `-c` kept on
all three commands (avoids the `fnox set`-without-`-c`-writes-committed-
fnox.toml footgun; docs bless provider-in-local-file). NOT the `sync` field
model — our cached values are opaque CacheEntry JSON, not source refs, so
`fnox set` fits. Bootstrap also ensures `*.local.toml` gitignored (exact
`fnox.local.toml` line also counts as covered; repo .gitignore line 582
already had `*.local.toml`). Project root: walk up from cwd for
`.git`/`fnox.toml`/`bakefile.py`, fallback cwd (mirrors fnox's own
discovery — `fnox config-files` walks up the same way; checked, not worth
spawning). Overrides unchanged: `FnoxCache.cache_file` ClassVar >
`BAKE_FNOX_CACHE_FILE` env > project default. Old central
`~/.cache/bake/secrets.toml` obsolete (user deletes, re-refresh).

**Provider name is load-bearing (FOUND via "does local override or merge?"
question):** fnox MERGES global + project + local configs; same-named
providers are replaced AS A UNIT (no deep-merge). `[providers.age]` in our
fnox.local.toml would clobber a project's committed `[providers.age]`
(age-in-git mode) for every fnox read in that repo. Hence distinct
`bake-cache-age` (originally `bake-sync-age`, fnox docs' own advice
pattern: "use a distinct name such as sync-age"; renamed 2026-10-11 —
no sync semantics, "cache" is what it is; existing fnox.local.toml
sed-renamed in place, key material unchanged). Tests updated (argv +
bootstrap block). Also fixed:
test_missing_age_key now pins cache_file fixture — it was hitting the real
repo fnox.local.toml via default path (stale leftover proved the hazard).

## Layering rule (why cache never handles the committed-encrypted pattern)

refreshable_cache = disposable layer (timestamps, TTL, refetch). Committed
encrypted values = durable layer (stable, reviewed, rotated deliberately).
Mixing breaks both: cache writes to a committed file = git churn on every
refresh; shared committed cache = stale blobs mask newer source values.
Committed-encrypted support = just mode 1 fnox.toml read through
`FnoxFetchFn`. Cache stays local-only, unconditionally.

## Cache invalidation rule (single source of truth)

If fnox daemon is enabled by the user for their shell workflow, our fetch must
bypass it (`--no-daemon`) so our keyring TTL/refresh stays the only invalidation
layer. Extra provider call per refresh = negligible.

## Plan

Step-by-step. Check off as done. Each phase ends with `bake lint` + targeted tests.

### Phase 0 — tooling via mise + keygen Space class

Repo convention (from `space/base.py` setup-dev): CLI tools are declared in
`.mise.toml` `[tools]` + `_get_mise_tools()` + `_get_required_cli_tools()`,
then `bake setup-dev` installs via mise. Brew is only for the platform layer
(mise itself). Both tools exist in mise registry (`age`, `fnox`).

Age keygen is NOT manual — new Space class makes it an idempotent
`setup-dev` step, same extension pattern `DvcSpace` uses.

- [x] Add `age = "latest"` and `fnox = "latest"` to `.mise.toml` `[tools]`
      (sorted, toml-sort cleans it in lint)
- [x] Add `"age"` and `"fnox"` to `_get_mise_tools()` and
      `_get_required_cli_tools()` — DONE in `FnoxSpace` overrides, NOT
      base.py (DvcSpace precedent: `dvc` tool likewise added in `DvcSpace`,
      base stays tool-agnostic)
- [x] New `FnoxSpace` class, `src/bakelib/space/fnox.py`:
      `class FnoxSpace(SecretUtils[T], BaseSpace)` — mirrors `DvcSpace`
      shape. Name reflects role: SecretUtils child wired to fnox. It
      overrides `_cache_registry_cls` → fnox-backed registry (Phase 3) AND
      ensures the fnox environment in setup_dev.
      `_cache_registry_cls` override deferred to Phase 3 (registry doesn't
      exist yet). Exported from `bakelib.space` + `bakelib` top-level.
- [x] `_ensure_age_key()`: skip if key file exists (idempotent), else
      Python `mkdir` (dry-run guarded) + `ctx.run(["age-keygen", "-o", ...])`
      (list argv, OS-agnostic); public key NOT printed (not needed). Key
      path = `fnox_age_key_file` pydantic field (constructor-injectable for
      tests), default `~/.config/fnox/age.txt`. No env fallback (user
      decision: field or default, nothing else)
- [x] Keygen hooked via `_setup_project` override (DvcSpace precedent), not
      `setup_dev` override
- [x] `assert_setup_dev` override: super() then `_assert_age_key()` —
      read-only existence check, safe under dry-run
- [x] Unit tests: `tests/unit/bakelib/space/test_fnox_space.py` — 10 passed
      (key exists = no keygen; missing = argv asserted; env override;
      assert paths; `_setup_project` hook)
- [x] Tools installed: `mise install` → age@1.3.2, fnox@1.39.0; keygen ran
      (chmod 600). Full `bake setup-dev` run deferred to user convenience —
      class now makes it idempotent either way
- [x] Verify: roundtrip works — `fnox set` → age ciphertext in toml,
      `fnox get` returns plaintext. FOUND (matters for Phase 2): - `fnox set -c <file>` FAILS if file doesn't exist (must touch first) - empty config errors "Provider 'age' not found" - provider block requires `recipients` (mandatory, no default):
      `[providers.age]` + `type = "age"` + `recipients = ["age1..."]` - ⇒ **FnoxCache must bootstrap the cache file**: on first set, if
      cache file missing/empty, write provider block with recipient =
      `age-keygen -y <key-file>` output before spawning `fnox set`

### Phase 1 — `FnoxFetchFn`

Files: `src/bakelib/refreshable_cache/fnox.py` (new module),
`tests/unit/bakelib/refreshable_cache/test_fnox_fetch_fn.py`

- [x] Write failing tests first: happy path (mock `subprocess.run`, assert
      argv `["fnox", "--no-daemon", "get", KEY]`, stdout stripped), fnox
      missing (`FileNotFoundError` → raise clear error naming fnox), nonzero
      exit (stderr surfaced), `--profile` passed when set. FINAL SHAPE (user
      call: one file, prefer real, drop mock duplicates) — single
      `test_fnox_fetch_fn.py`, 7 tests / 0.3s: 2 mocked argv-shape (unique
      assertions real runs can't make), 2 frozen/key contract, 2 REAL
      roundtrip + missing-key (skip-guarded, `mise which` shim resolution,
      tmp cwd), 1 real missing-binary via PATH removal. Deleted: separate
      `test_fnox_fetch_fn_real.py`, mocked strip/stderr tests (real tests
      cover them)
- [x] Implement as frozen dataclass per `FetchFn` pattern (NOT `__init__`
      class — the doc sketch above predates checking `utils.py`):

      ```python
      @dataclass(frozen=True)
      class FnoxFetchFn(FetchFn[str]):
          profile: str | None = None

          def __call__(self) -> str:  # subprocess fnox --no-daemon get key
      ```

- [x] `bake lint` + targeted tests pass. REAL roundtrip verified: scratch
      dir + age provider block, `fnox set --provider age` (ciphertext in
      toml), `FnoxFetchFn` returned exact plaintext. NOTE: running outside
      a mise-configured dir, spawned `fnox` shim errors "No version is set
      for shim: fnox" — surfaced verbatim by the nonzero-exit path (error
      handling proven on real failure). Same known shim quirk as Phase 0
      keygen; real projects have `.mise.toml` so unaffected. Real roundtrip
      tests live in the unit dir (user call: integration = minutes-slow
      only, subsecond real tests run with unit). Test layout per the FINAL
      SHAPE note above

### Phase 2 — `FnoxCache` backend

Files: `src/bakelib/refreshable_cache/fnox.py` (merged — user call:
one fnox module, fnox_cache.py deleted after Phase 2; the split was a plan
artifact and the cache already imported run_fnox/DEFAULT_AGE_KEY_FILE back
from fnox.py), `tests/unit/bakelib/refreshable_cache/test_fnox_cache.py`

- [x] Mirror `KeyringCache` shape (subclass `RefreshableCache`, implement
      `_get_entry`/`set`/`delete`, same logger.debug style)
- [x] Bootstrap writes `key_file = <FnoxSpace default/field>` into the
      provider block alongside `recipients` — fnox lookup order honors
      provider `key_file`, so our path is authoritative and fnox's own
      default (`~/.config/fnox/age.txt`) can drift without breaking us.
      (Unit tests can't catch that drift, they assert our own constant.)
      Keygen keeps writing the default so plain shell `fnox` still finds
      the key. Bootstrap also mkdir parent + chmod 0600; skips when file
      non-empty (real fnox rewrites toml on set, so idempotence asserted
      at the skip-logic level, mocked)
- [x] Cross-module test: `AGE_KEY_FILE` ==
      `FnoxSpace()._age_key_file()` default — pins FnoxCache and FnoxSpace
      to the same path (catches OUR two modules drifting apart; does NOT
      catch fnox's own default changing, only real fnox run or a version
      pin catches that). UPGRADED to SSOT (user call): the constant now
      lives once, as `DEFAULT_AGE_KEY_FILE` in
      `bakelib/refreshable_cache/fnox.py` (leaf module — cache layer must
      not import spaces, and package `__init__` creates no cycle).
      `FnoxSpace._age_key_file()` = `fnox_age_key_file field or
DEFAULT_AGE_KEY_FILE`; `FnoxCache.age_key_file: ClassVar[Path | None]`
      overrides the same default. Cross-module tests now assert both fall
      back to the shared constant
- [x] Constants: `FNOX_CACHE_FILE = ~/.cache/bake/secrets.toml` (env
      override `BAKE_FNOX_CACHE_FILE`, read at call time so tests can
      monkeypatch)
- [x] All three commands via `run_fnox` (shared helper in fnox.py):
      `--no-daemon -c <path>` prefix; `set` always passes `--provider age`
      (plaintext footgun guard); delete tolerates missing key. FOUND (real
      tests): fnox secret names must be valid env-var names — `namespace:key`
      rejected, `_get_full_key()` overridden to
      `re.sub(r"[^A-Za-z0-9_]", "_", f"{ns}__{key}")`
- [x] Guardrails: never touch project `fnox.toml` (`-c` guarantees this);
      `--no-daemon` always (TTL is sole invalidation source)
- [x] Behavior when fnox binary missing: raise loud error (do NOT silently
      fall through — different from keyring; missing tool = user must know)
- [x] Tests FINAL SHAPE (10 tests / ~0.4s, no skipif — user rule: tests
      FAIL when fnox missing, never skip; `_real_bin` + PATH fixture keep
      working from tmp cwd via `mise which`): 3 mocked argv-shape (get /
      set+`--provider age` / remove, value asserted as CacheEntry JSON),
      1 mocked bootstrap-skip (fnox rewrites toml on set, so idempotence
      is our-skip-logic only), 1 cross-module key path, 4 REAL (bootstrap
      provider block, chmod 0600, missing age key loud, full roundtrip
      miss→set(encrypted)→hit→delete). FOUND (leak, real test): `run()`
      DEBUG-logs argv at `[run]`/`[done]` even with echo=False — and
      `[done]`/`[error]` extras carry captured stdout (= secret on `get`).
      Fix: `run_fnox()` helper sets `bake.ui.run.main` logger to
      CRITICAL+1 around the spawn, restores in finally
- [x] `bake lint` + targeted tests pass (17/17 incl. fetch fn file)

### Phase 3 — fnox-backed registry + opt-in wiring

Files: `src/bakelib/refreshable_cache/registry.py`,
`src/bakelib/space/fnox.py`, `bakefile.py`,
`docs/bakelib/{cache,secrets,spaces}.mdx`,
`tests/unit/bakelib/refreshable_cache/test_registry.py`,
`tests/unit/bakelib/space/test_fnox_space.py`

- [x] New `SecretUtilsFnoxCacheRegistry(RefreshableCacheRegistry[T])` next to
      the keyring one: `_backends = [MemoryCache, FnoxCache]`,
      `namespace = "bakebook"`
- [x] `SecretUtilsKeyringCacheRegistry` stays untouched (existing projects
      keep keyring; no destructive swap)
- [x] `FnoxSpace._cache_registry_cls = SecretUtilsFnoxCacheRegistry[T]`
      (deferred since Phase 0 — now wired). MRO verified live: dogfooded
      `MyBakebook(GitHubActionsTools, PythonLibSpace, FnoxSpace)` resolves
      `_cache_registry_cls` to the fnox registry (FnoxSpace defines the
      attr; keyring default only lives on `SecretUtils`, later in MRO).
      NOTE: bakefile's `MyBakebook` overrides `get_secret_namespace()` →
      "bakefile" (registry class default "bakebook" only applies when not
      overridden)
- [x] bakefile's own `MyBakebook` adds `FnoxSpace` mixin (dogfood). Live
      smoke: `bake secret list` builds the fnox-backed vault (both tracked
      keys "not cached"), no fnox spawn on registry construction
- [x] Targeted tests: `TestSecretUtilsRegistries` in test_registry.py
      (keyring shape untouched, fnox shape, fnox builds ChainedCache
      Memory+Fnox); `test_vault_uses_fnox_backends` +
      `test_base_secret_utils_keeps_keyring` in test_fnox_space.py
      (base SecretUtils still keyring)
- [x] Docs: secrets.mdx (FnoxSpace opt-in snippet), cache.mdx (FnoxCache
      backend bullet), spaces.mdx (prebuilt spaces list)
- [x] Full `bake test` + `bake lint` before commit (2475 passed / 3 xfailed,
      99% coverage; lint exit 0)

## Status

- [x] Phase 0 tooling + `FnoxSpace` + keygen — DONE 2026-10-10
- [x] Phase 1 `FnoxFetchFn` + tests — DONE 2026-10-10
- [x] Phase 2 `FnoxCache` backend + tests — DONE 2026-10-10
- [x] Phase 3 registry swap + docs — DONE 2026-10-10
- [x] Keyring ACL pain — FIXED 2026-10-09 (see Keyring Pain Resolution below)

## fnox facts verified from docs

- `fnox remove KEY` (aliases `rm`, `delete`) — delete a secret
- `fnox set KEY VALUE --provider age` — no provider selected = PLAINTEXT in
  toml, footgun to guard against
- `fnox --no-daemon` bypasses the opt-in memory daemon
- `-c <path>` with non-default filename disables hierarchical search and local
  overrides (fine for the bake-managed cache store; incompatible with
  `fnox sync --local-file`)
- `fnox.local.toml` = gitignored local overrides, per project; `fnox sync
--local-file` pulls provider values into it (alternative to FnoxFetchFn for
  per-project flow)
- age identity: `FNOX_AGE_KEY_FILE` env or `key_file` in provider config;
  recipients list supports multiple pubkeys incl. SSH keys

## Keyring pain resolution (2026-10-09)

**Symptom:** keychain dialog asked for login password on "Always Allow",
rejected the correct password, only Deny worked. Plain Allow worked for the
session only.

**Root cause:** login keychain password had drifted from the macOS login
password. "Always Allow" prompts for the _keychain_ password, not the account
password. With the mismatch, correct login password was forever rejected.

**Diagnosis:**

- `security unlock-keychain login.keychain-db` (fails with "password
  incorrect" when mismatched)
- repro: read an old item via venv python keyring lib →
  `keyring.errors.KeyringLocked: (-128, 'Keychain Access Denied')`
- Inside bake the failure is silent: `ChainedCache` catches the exception
  (cache.py `_get_entry`), falls through to MemoryCache, refetches. The
  visible prompt came from the later `set_password` path.

**Fix:** `security set-keychain-password login.keychain-db` (old = previous
keychain password, new = current login password). Equivalent GUI path:
Keychain Access → login → Edit → Change Password.

**Verified:** fresh uv venv (different binary path) reads items with no
prompt. ACL is keyed to the base uv interpreter
(`~/.local/share/uv/python/cpython-3.14-*/bin/python3.14`), which all venvs
symlink to, so the fix survives `uv sync` / venv recreation for that python
version.

**Remaining rule of thumb:** if prompts ever return after a python version
upgrade, one "Always Allow" for the new base interpreter is enough.

## Bitwarden remote dogfood + run_fnox env fix (2026-10-10)

Live end-to-end with real Bitwarden Secrets Manager (user's account, project
`dd6bd5c9-...`): scratch bakebook in /tmp/fnox-play, `MyBakebook(SecretUtils[str],
FnoxSpace)` with `FnoxFetchFn(key="REMOTE_TOKEN")` → `fnox get` resolves via
committed `fnox.toml` pointer (`provider = "bw"`) → bws CLI → BWS API → cached
age-encrypted in project `fnox.local.toml`. `bake secret refresh/get/list` all
green, zero plaintext at rest.

**Bug found + fixed:** `bake.ui.run`'s `_prepare_subprocess_env` force-sets
`FORCE_COLOR=1` + `CLICOLOR_FORCE=1` on captured children. bws checks
_presence_ (empty value still colors), emits ANSI JSON, fnox parse fails:
`invalid response: Failed to parse JSON`. Can't blank via run()'s env param
(setdefault re-adds; empty string still colors). **Fix:** `run_fnox` now
spawns via direct `subprocess.run(capture_output=True, text=True, check=False)`
with env filtered (`FORCE_COLOR`/`CLICOLOR_FORCE` removed). Strictly better
for secrets anyway: no bake.ui.run DEBUG log extras carrying argv/stdout.
Removed now-dead `FileNotFoundError` re-wraps in `FnoxFetchFn.__call__` and
`FnoxCache._fnox` (run_fnox raises `RuntimeError(_fnox_missing_error())`
itself); dropped `from bake.ui import run` import. 89 fnox tests pass, lint 0.

Side learnings (global machine setup, not repo):

- Bitwarden SM: access tokens attach to machine accounts only, free plan =
  unlimited secrets / 3 projects / 3 machine accounts. `bws` CLI not in
  mise/brew, installed `~/.local/bin/bws` from bitwarden/sdk-sm releases.
- bitwarden-sm provider auth reads REAL env only (fnox source: `env::var`)
  — config-stored `BWS_ACCESS_TOKEN` is NOT auto-injected. Pattern: store
  age-encrypted in `~/.config/fnox/config.toml` (global), decrypt in shell
  rc: `export BWS_ACCESS_TOKEN="$(fnox -c ~/.config/fnox/config.toml get
BWS_ACCESS_TOKEN)"`.
- fnox global config = `~/.config/fnox/config.toml` (fixed path); wizard's
  stray `fnox.toml` in that dir deleted (merged its age provider in first).
- bws state-file/JSON quirks documented in fnox source
  `crates/fnox-core/src/providers/bitwarden_sm.rs`.

## Bootstrap credentials: env-only resolution (2026-10-11, FOUND live)

fnox resolves provider credentials (FNOX_BWS_ACCESS_TOKEN, BWS_ACCESS_TOKEN)
from ENV ONLY — a secret in any config store (global/fnox.toml/fnox.local.toml)
never authenticates on its own. Verified: stored both spellings age-encrypted
in fnox.local.toml, plain `fnox get REMOTE_TOKEN` still auth_failed. Docs
(bitwarden-sm page) list env vars only; docs' "store with age for bootstrap"
pattern implies `fnox exec` (which exports secrets to child env). CORRECTS the
earlier "fnox resolves from the config merge" claim (fnox-setup section).

**Design:** bake replicates fnox-exec env export, lazily.
`fnox_bootstrap_secrets: ClassVar[Mapping[str,str]]` on FnoxSpace (base empty —
provider-agnostic; name -> prompt label, names follow fnox's
FNOX_<PROVIDER>_* convention). `inject_bootstrap_env(names, cache_file)` in
refreshable_cache/fnox.py: per name missing from os.environ, age-only
`fnox -c fnox.local.toml get <name>`, set os.environ (env wins, never
overwritten — CI/user's own export stays). FnoxSpace.vault() calls it before
any fetch. setup-dev path: `_ensure_bootstrap_secrets` (probe → optional
typer.confirm → hidden paste → `fnox set --provider bake-cache-age`), assert
counterpart read-only. Optional prompt (decline = skip + info), fixed earlier
double `_ensure_age_key` call. Plain `bake -b bb bw-demo` now works: no env,
no `fnox exec`. os.environ mutation scoped to the bake process (same exposure
as fnox exec wrapping).

## Bootstrap ownership moved to registry (2026-10-11)

Bootstrap mechanics now live on `SecretUtilsFnoxCacheRegistry` (registry.py),
not the space: `bootstrap_secrets` init kwarg + `inject_bootstrap_env()`
(fires lazily from `insert_cache`, before any fetch; caller-owned
`_bootstrap_missing` memo per registry instance — module global gone) +
`ensure_bootstrap_secrets(*, dry_run)` (confirm + hidden paste loop) +
`assert_bootstrap_secrets()`. `FnoxCache.ensure/resolve_cache_file`
classmethods kept as store-path primitives. SecretUtils gained
`_cache_registry_kwargs()` hook (base `= {}`), vault() passes it. FnoxSpace
narrowed `vault()` return type to `SecretUtilsFnoxCacheRegistry[T]` (covariant
override, one cast) so wrappers call `self.vault().ensure_...()` directly.
dry_run read stays in the space wrapper (command context) — no
ContextNotAvailableError fallback hack. Missing-name WARNING in
inject_bootstrap_env dropped: store-absent `secret list` stays clean, the
fetch-failure error + `_auth_failed_hint` carries the actionable message.

Command moved into FnoxSpace (was TEMP Trybook method):
`setup-fnox` (`setup_fnox`: _ensure_age_key + _ensure_bootstrap_secrets).
No assert-fnox — assert-setup-dev -ff already covers the fnox asserts via the
FnoxSpace.assert_setup_dev override. Hints updated (`bake setup-fnox`). CLAUDE.md
bakebook2 example de-fnox'd (generic foo-setup). Live-verified: assert-fnox
SUCCESS on restored fnox.local.toml, secret list clean with store absent.

## Bootstrap knowledge out of SecretUtils (2026-10-11)

secret_list's getattr duck-typing on bootstrap (bootstrap_secrets /
has_bootstrap_value) was a layering leak. Now: base RefreshableCacheRegistry
gained `list_entries() -> list[tuple[str, bool]]` (sorted, has_value);
SecretUtilsFnoxCacheRegistry overrides it appending bootstrap entries via
has_bootstrap_value. secret_list renders generic (name, cached) pairs —
no getattr, no Mapping import, no bootstrap/fnox mention in SecretUtils.
`setup-fnox`/`assert-fnox` commands moved into FnoxSpace (assert-fnox dropped
— assert-setup-dev covers it); bootstrap-path error hints say `bake
setup-fnox`, kept `setup-dev` only for missing binaries. Live: `bake -b bb
secret list` merges bootstrap into one sorted list; keyring path unchanged.

## Full unification: bootstrap = regular tracked secrets (2026-10-11)

Final form after user challenge "why mismatch behavior between bootstrap and
other secret, make everything the same":

- **Storage**: bootstrap secrets are regular tracked vault keys. Stored
  namespaced (`bakebook__FNOX_BWS_ACCESS_TOKEN`) via `FnoxCache.set` — same
  shape as every secret. Old raw-named entry orphaned; migration = re-paste
  via `bake setup-fnox` (user choice, no compat code).
- **FetchFn**: `BootstrapFetchFn(FetchFn[str])` in
  `refreshable_cache/fnox.py` — local store is the ONLY source (chicken-and-
  egg); store miss = clean `console.error` + `typer.Exit(1)` with `bake
setup-fnox` hint (label-aware). NOT NullFetchFn: it returns None which
  `_fetch` would store (poisons store), and gives no hint.
- **Registration**: FnoxSpace appends `BootstrapFetchFn`s in
  `get_secret_fetch_fns()`; base `vault()` registers them. No
  `ensure_cache` override loop.
- **Env injection**: `_setup_vault(vault)` — new post-build hook on
  SecretUtils (`vault()` calls it once after memoized build). FnoxSpace
  exports each bootstrap secret to env when absent (env wins). Why vault
  chokepoint: every secret access goes through it; fnox reads provider
  creds from ENV ONLY, export must precede any provider-backed fetch.
- **Deleted**: registry `bootstrap_secrets` kwarg, `has_bootstrap_value`,
  `ensure/assert_bootstrap_secrets`, `list_entries` override,
  `inject_bootstrap_env` method, `_bootstrap_missing` memo,
  `_cache_registry_kwargs` hook (SecretUtils + FnoxSpace override),
  module-level `inject_bootstrap_env`. `SecretUtilsFnoxCacheRegistry` back
  to plain 2-class-attr subclass. FnoxSpace `vault()` override gone.
- **Uniform surface**: `secret get/set/del/refresh/list` identical for
  bootstrap and other secrets. `secret del` no-key = deletes everything
  incl. bootstrap (user choice, assert catches). list_entries hook means
  `secret list` generic; registry `list_entries` now base-only.

Live: `bake -b bb secret list` shows FNOX_BWS_ACCESS_TOKEN: not cached
(re-paste pending). `bake -b bb secret get FNOX_BWS_ACCESS_TOKEN` → clean
`bake setup-fnox` hint. 743 tests, ruff + ty clean.
