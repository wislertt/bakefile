# Cache lives in the project's `fnox.local.toml` under provider `bake-cache-age`

The cache file is `<project root>/fnox.local.toml` (gitignored), not a central file under `~/.cache`. A central file made the first repo's age `key_file` win and silently ignored later repos'. Project root is found by walking up from the cwd for `.git`, `fnox.toml` or `bakefile.py`. Overrides: the `FnoxCache.cache_file` class attribute, then `BAKE_FNOX_CACHE_FILE`.

The provider block is named `bake-cache-age`, never `age`: fnox merges global, project and local configs, and a same-named provider is replaced as a whole. A plain `age` provider would clobber a project's committed one for every fnox read in that repo. Every cache command passes `-c`, so `fnox set` can never write to the committed `fnox.toml`.
