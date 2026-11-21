# The cache is a disposable layer and never holds committed secrets

The refreshable cache is local-only, with timestamps, TTL and refetch. Committed encrypted values are a durable, reviewed layer, rotated deliberately. Mixing them breaks both: a cache writing into a committed file churns git on every refresh, and a shared committed cache lets stale blobs mask newer source values. Committed-encrypted storage is supported only as a `fnox.toml` read through the fetch function.

Our fetch always passes `--no-daemon`. Even if the user enabled the fnox daemon for their shell, our TTL stays the only invalidation layer, at the cost of one extra provider call per refresh.
