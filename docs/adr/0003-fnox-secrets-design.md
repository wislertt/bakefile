# fnox secrets: remote vault is the source, a disposable local age cache sits in front

Secrets resolve from a remote vault (1Password, AWS Secrets Manager, Bitwarden and others) through `fnox get`, with `fnox.toml` committed holding references only. A local age-encrypted file caches the values. Storage strategy stays the user's choice in `fnox.toml`, so one fetch function covers every mode.

## Source and cache

Rejected as the recommended default: age-encrypted secrets committed to git. Multi-recipient age needs teammate public keys collected upfront and re-encryption on every join. Departures force rotating every real secret, because git history keeps the old ciphertext forever. A remote vault gives team sharing, MFA and instant revocation without that ceremony.

The cache replaced the macOS-keychain backend: no ACL prompts, encrypted at rest, portable.

## Cache location

The cache file is `<project root>/fnox.local.toml` (gitignored), not a central file under `~/.cache`. A central file made the first repo's age `key_file` win and silently ignored later repos'. Project root is found by walking up from the cwd for `.git`, `fnox.toml` or `bakefile.py`. Overrides: the `FnoxCache.cache_file` class attribute, then `BAKE_FNOX_CACHE_FILE`.

The provider block is named `bake-cache-age`, never `age`: fnox merges global, project and local configs, and a same-named provider is replaced as a whole. A plain `age` provider would clobber a project's committed one for every fnox read in that repo. Every cache command passes `-c`, so `fnox set` can never write to the committed `fnox.toml`.

## The cache is a disposable layer

The refreshable cache is local-only, with timestamps, TTL and refetch. Committed encrypted values are a durable, reviewed layer, rotated deliberately. Mixing them breaks both: a cache writing into a committed file churns git on every refresh, and a shared committed cache lets stale blobs mask newer source values. Committed-encrypted storage is supported only as a `fnox.toml` read through the fetch function.

Our fetch always passes `--no-daemon`. Even if the user enabled the fnox daemon for their shell, our TTL stays the only invalidation layer, at the cost of one extra provider call per refresh.

## Bootstrap secrets are regular tracked secrets

fnox reads provider credentials (for example `BWS_ACCESS_TOKEN`) from the environment only, never from any config file. The bootstrap secret is therefore stored in the cache like any other, under the same namespaced key. Its fetch function (`BootstrapFetchFn`, a `UserInputFetchFn`) takes the value only from the user: it prompts on a terminal, and empty input or no terminal declines, so refresh keeps the stored value. A post-build hook on the vault exports each one into `os.environ` before any provider-backed fetch, and an existing env value always wins.

Earlier versions special-cased bootstrap secrets with a separate raw-named store, ensure and assert paths, and a `getattr` check in `secret list`. That left `secret get/set/del/refresh/list` behaving differently for two kinds of secret, so it was removed.
