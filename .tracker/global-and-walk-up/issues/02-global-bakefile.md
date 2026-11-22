# 02: Global `bakefile.py`

Status: resolved

Blocked by: 01 (Walk-up and invocation directory)

Spec: `.tracker/global-and-walk-up/spec.md`. Decision: `docs/adr/0005-one-bakefile-per-run-no-merging.md`.

**What to build:** A user can keep a Global `bakefile.py` (for example by symlinking a dotfiles repo to `~/.config/bake`) and run its commands from anywhere. `bake -g <cmd>` always uses it. Plain `bake <cmd>` falls back to it when walk-up finds nothing and the user has created one. `bakefile -g ...` manages it, and `bakefile -g init` creates it. Having no Global `bakefile.py` changes nothing except the clearer not-found message.

- [x] Global directory is `BAKE_CONFIG_DIR`, else `$XDG_CONFIG_HOME/bake`, else `~/.config/bake`, on every platform, read through the settings object
- [x] `-g` / `--global` on both CLIs; `bake -g <cmd>` uses the global file even inside a project with its own `bakefile.py`
- [x] `bake -g -f mac.py <cmd>` uses `mac.py` in the global directory
- [x] `-g` together with `-C` is a usage error
- [x] `bake -g` with no global file errors, names the global path and suggests `bakefile -g init`
- [x] A symlinked global directory runs commands in the resolved real directory
- [x] `bakefile -g lock/add/sync` act on the Global `bakefile.py`
- [x] `bakefile -g init` creates the global directory if missing and writes a Global `bakefile.py`; plain `bakefile init` is unchanged
- [x] When walk-up finds nothing, `bake` and `bakefile` fall back to the global file with the same file name (`-f` included), only if it exists
- [x] `-C` never falls back
- [x] A command missing from the chosen Bakebook is an error, never looked up in another file
- [x] `bake --help` marks the loaded file as global when it is; a debug log line records which resolution step matched; no notice on normal runs
- [x] Not-found message says it searched the start directory and parent directories (or the exact `-C` directory) and always shows a `Global:` line with the global path and whether it exists
- [x] Hints that name `bakefile.py` (such as the broken-environment hint after re-invocation) print the resolved absolute path
- [x] Integration test: a Bakefile-level Global `bakefile.py` run with `-g` from an unrelated directory re-invokes under its own environment and reports the right file and Invocation directory
- [x] `GLOSSARY.md` terms used: Global `bakefile.py`

## Comments

- Implemented on `feat/global-bakefile` (branched from `chore/docs-site`).
- `call_app_with_chdir` skips the directory change when the `bakefile.py`'s directory does not exist, so `bakefile -g init` can run before the global directory exists.
- Kept the `call_app_with_chdir` guard as is (decided in review): the directory can only be missing with `-g` before the global directory exists, and there it turns a `FileNotFoundError` traceback into a clean not-found error.
- For ticket 03: the not-found message changed from `Directory not found: …` to `Searched in: <dir> and parent directories` plus a `Global: <path> (exists|not found)` line. User docs and the changelog should show the new text.
- Known gap: `bakefile -g lock` (and other subcommands) with no global file print `Bakefile not found at <path>` without suggesting `bakefile -g init`, unlike `bake -g`.
- If integration tests run old code in a re-invoked script environment, uv reused a stale build of the local package: run `uv cache clean bakefile`. Candidate for `CONTRIBUTING.md` or troubleshooting docs in ticket 03.
