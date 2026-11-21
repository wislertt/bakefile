# Bootstrap secrets are regular tracked secrets

fnox reads provider credentials (for example `BWS_ACCESS_TOKEN`) from the environment only, never from any config file. The bootstrap secret is therefore stored in the cache like any other, under the same namespaced key. Its fetch function reads only the local store (a miss prints a `bake setup-fnox` hint). A post-build hook on the vault exports each one into `os.environ` before any provider-backed fetch, and an existing env value always wins.

Earlier versions special-cased bootstrap secrets with a separate raw-named store, ensure and assert paths, and a `getattr` check in `secret list`. That left `secret get/set/del/refresh/list` behaving differently for two kinds of secret, so it was removed.
