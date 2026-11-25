# 01: Managed files end to end, fixed text only

Status: resolved

Blocked by: None (can start immediately)

Spec: `.tracker/managed-content/spec.md`. Decision: `docs/adr/0006-managed-files-and-bake-lock.md`.

**What to build:** A repo with `bake_manage_content` on gets `oxfmt.config.ts` from `BaseSpace` as a managed file: `setup-dev` and `mc sync` write it with the header, `bake.lock` records it, `lint` reports drift before any formatter runs, `--force` restores it, and a file no Space produces any more is deleted. With the toggle off nothing changes. Templates in this ticket have fixed text only; editable blocks come in 02, bakefile values in 04.

- [x] `bake_manage_content: bool = False` on `BaseSpace`, settable in `bakefile.py` or by `BAKE_MANAGE_CONTENT=true`
- [x] Toggle off: no write, no drift check, no `bake.lock`, no output; `mc sync` and `mc lock` exit nonzero with a hint on how to turn it on
- [x] Managed-files hook on `BaseSpace`, composed with `super()`; a declaration is a package anchor and a template name, read from `<package>/managed/<name>` through `importlib.resources`; the most-derived Space on the MRO wins a path
- [x] Header `managed by bakefile; edit only the parts marked "editable"` on line 1 in the comment syntax from the spec's table; plain `.json` and unknown types fail at template load
- [x] Read and hash after normalisation (strip UTF-8 BOM, CRLF to LF, add final newline); write LF, no BOM, final newline; a file with equal normalised content is not rewritten
- [x] `bake.lock` per ADR 0006: `version`, `revision`, `[managed-content."<path>"]` with `template` (`<distribution>:<name>`) and `hash` of the normalised bytes; an unparsable lock exits 2 with the `mc lock` hint
- [x] `managed-content` command group with hidden alias `mc`: `lock` (rebuild from the files), `sync` (`--dry-run`, `--force`)
- [x] `setup-dev` locks and syncs at the end of `BaseSpace`'s project step
- [x] `lint` relocks, then checks drift in `BaseSpace`'s fast step before oxfmt; drift exits 1 with a hint to run `mc sync`
- [x] A file that does not match reports `expected '<line>', but line N is '<text>'` and exits 2; `--force` overwrites it
- [x] A locked file with its header missing is an error
- [x] A file in the lock that no Space produces is deleted with its lock entry; a hand file created later at that path is left alone
- [x] Any error writes nothing; exit codes 0 clean, 1 drift, 2 error
- [x] `BaseSpace` ships `oxfmt.config.ts` as a whole fixed file (content as this repo's own)
- [x] This repo's oxfmt ignores the `managed/` template directories
- [x] Parametrised template test over every managed file a bakelib Space declares: sync into an empty project with the toggle on, `oxfmt --check` with the shared config, no trailing whitespace and no whitespace-only lines (the `trailing-whitespace` pre-commit hook would strip them, and oxfmt re-adds indentation to an empty line inside a code block in a list, so the two hooks fight), a second sync changes nothing
- [x] Integration test: build the wheel and resolve every declared template through `importlib.resources`
- [x] Tests drive Space commands in a temporary project with the mocked context; engine edge cases use test Spaces in a small test package with fixture templates
- [x] `GLOSSARY.md` terms used: Managed content, Managed file, Template, `bake.lock`, Drift

## Comments

Implemented in `src/bakelib/managed_content/` (engine, command layer) and `BaseSpace`. Decisions made along the way:

- Global `bake --dry-run` also writes nothing, like `mc sync --dry-run`; `lint` still checks drift but skips the relock write.
- Until 02 lands, a template containing `{%` or `{{ bakefile` fails at load ("tags are not supported yet"). 02 replaces this check with the grammar.
- A template whose lock hash still matches the file is rewritten (the upgrade path from ADR 0006), since fixed-text templates change between releases too.
- `bake.lock` with a `version` other than 1, or a path outside the project, exits 2 with the `mc lock` hint; `mc lock` rebuilds it.
- The `mc` alias is registered by overriding `_get_or_create_group` in `BaseSpace`. A generic group alias in `bake`'s `GroupKwargs` would be cleaner; left for later.
- The template key of an editable install is found through `direct_url.json`, since editable installs list no module files.
- Open: user story 10 in the spec says `bake_manage_content = True`; pydantic needs the annotation (`bake_manage_content: bool = True`) in a subclass.
