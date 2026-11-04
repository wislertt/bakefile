# Plan: bump requires-python from 3.10 to 3.11

Planned: after vacation, ~2026-10-28. Ship as ONE separate PR, nothing else mixed in.

## Why

- Python 3.10 hit EOL 2026-10 (python.org stopped security fixes). bakefile drops at EOL per common practice for tools.
- Main win: stdlib `tomllib` (3.11+). Deletes the entire tomli fallback: import guards, dependency pins, markers, and the dev-group tomli that exists only so `ty` can resolve the fallback branch (added during the 3.15 bump, PR #144).
- Other 3.11 gains available later: `ExceptionGroup`/`except*`, `Self`, `StrEnum`, faster startup.

## Context

- bakefile is hybrid: runner CLI + importable library (`from bake import ...`, `from bakelib import ...`, bakebooks distributed as packages, see `examples/python-package`).
- Pre-1.0, so floor bump is semver-free. After tagging 1.0, treat floor bumps as breaking for downstream bakebook authors.
- Precedent for scope of a version bump: PR #144 (python 3.15 adoption).

## Changes

1. **`pyproject.toml`**
    - `requires-python = ">=3.10"` → `">=3.11"`
    - Classifiers: drop `3.10`, keep `3.11`-`3.15`
    - `dependencies`: delete `"tomli>=2.0.0; python_version < '3.11'"`
    - `locked` extra: delete `"tomli==2.5.0; python_version < '3.11'"` (respect any `# hold` comment policy via `bake update`)
    - dev group: delete the unmarked `"tomli>=2.0.0"` added in PR #144
2. **Source**: delete both version-guard import blocks, replace with plain `import tomllib`
    - `src/bake/manage/add_inline.py` (~lines 13-17)
    - `src/bakelib/space/rust.py` (~lines 19-23)
3. **`uv.lock`**: regenerate (`uv lock`)
4. **CI**: `.github/workflows/test.yml` matrix `['3.10', ...]` → `['3.11', ..., '3.15']`
5. **Docs**
    - `README.md` + `docs/index.mdx`: badge drop `3.10`
    - `docs/getting-started/installation.mdx`: "supports Python 3.11 through 3.15"
    - `docs/skill.md`: "Requires Python 3.10+" → "3.11+"
6. **Sweep**: `grep -rn "3\.10\|tomli" src/ tests/ docs/ examples/ README.md` for leftovers
    - Check `examples/python-package/uv.lock` + `examples/simple/bakefile.py.lock` (regenerate via `bake update`)

## Out of scope

- Adopting any 3.11+ language features beyond deleting the tomli fallback. Separate follow-ups.
- `sys.version_info` guards for versions > 3.11, if any exist, stay as-is.

## Verification

- `bake lint` (ruff + ty + deptry + actionlint + lock pin check)
- Targeted tests for touched files: `uv run pytest tests/unit/bake/manage/ tests/unit/bakelib/space/ -v`
- CI green on matrix 3.11-3.15 (ubuntu/windows/macos)

## Decision record

- Drop-at-EOL chosen over loguru-style generous floor: bakebooks run via `bake` on user-pinned pythons, no legacy import-freeze use case; compat-shim tax (tomli guards) outweighs hypothetical 3.10 users.
- Considered and rejected: SPEC 0 style early drop (3 years post-release). For heavy-CI native-build projects; bakefile is pure python.
