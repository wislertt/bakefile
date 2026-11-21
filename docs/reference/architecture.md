# Architecture

How `bake` and `bakefile` load and run. Not a review rule set; coding rules live in `CODING_STANDARDS.md`, vocabulary in `GLOSSARY.md`, decisions in `docs/adr/`.

## Load flow

`bake -C /path build --prod`:

1. `get_bakefile_object()` parses the shared options (`-C`, `--file-name`, `--book-name`, `--dry-run`, verbosity) into a `BakefileObject`.
2. `BakefileObject.get_bakebook()` resolves the path (`resolve_bakefile_path`), imports the file (`load_module`), and extracts and validates a `Bakebook` instance (`bake/bakebook/get.py`).
3. The Bakebook's own Typer app runs `["build", "--prod"]`.

`bakefile` (management CLI) follows the same flow but loads the Bakebook optionally and does not warn when none is found.

## Why `BakefileObject`

Both CLIs carry parsed options in one `BakefileObject` instead of threading arguments through every call. It is also the single source of truth for `dry_run`: `Context.dry_run` reads `self.obj.dry_run`. `get_bakefile_object()` parses args through a hidden Typer app, filtering out `--help` and `--version` so it cannot interfere with the real CLI.

## Context and circular imports

`Context` (a `typer.Context` subclass with typed `obj: BakefileObject`) is re-exported from `bake`. In `bake/cli/common/params.py` and `obj.py`, use `typer.Context`, not `Context`, to avoid circular imports. Everywhere else (user-facing CLI commands, tests), import `Context` from `bake`.

## Bakebook samples

`src/bake/samples/` modules use `__bakebook__` as the bakebook variable name. `init` rewrites it to the name the user chose.

## Module caching

`load_module` imports every bakefile.py under the fixed module name `bakefile` and stores it in `sys.modules`, so one Python process loads one bakebook. Load several with separate subprocesses.

## Python detection (two levels)

| Level          | Trigger                                | Environment                                    |
| -------------- | -------------------------------------- | ---------------------------------------------- |
| Bakefile-level | PEP 723 inline metadata in bakefile.py | file-isolated venv (`uv python find --script`) |
| Project-level  | no inline metadata                     | project `.venv` (`uv python find -v`)          |

`bakefile add/lock/sync` require inline metadata and inject `--script bakefile.py`; `bakefile pip` works at both levels and injects `--python <path>`. All of them forward arguments to uv unparsed, so new uv options work without changes.

## Maintaining the `locked` extra

Rationale in `docs/adr/0002-two-dependency-channels.md`. Mechanics:

- `scripts/locked_pins.py` guard (run by `bake lint`) enforces: base set is a subset of locked set, every locked entry is exact `==`, pin >= floor, pin == `uv.lock` version, lock satisfies floors.
- `bake update` (`DevUtils._update_locked_pins` in `bakefile.py`): `relax_locked_pins`, then `uv lock --upgrade`, then `rewrite_locked_pins`. A crash between relax and rewrite leaves non-exact pins; the guard fails lint and rerunning `bake update` heals it.
- Hold a pin with a trailing `# hold` comment (regex `#\s*hold\b` on the rendered array, since tomlkit hides trailing comments). Release by deleting it and running `bake update`.
- bakelib's default mise tool is `pipx:bakefile[extras=locked]`. Existing bare `pipx:bakefile` installs count as satisfied and never gain the extras; one manual `mise use 'pipx:bakefile[extras=locked]'` migrates.
