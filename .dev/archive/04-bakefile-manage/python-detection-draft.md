# Bakefile Python Environment Management - DRAFT NOTES

**Status:** SUPERSEDED BY TASK 05 (COMPLETED)
**See:** `.dev/archive/05-find-python/`

---

## These are early draft notes kept for reference

The Python detection feature described here was implemented in task 05.

## repo level

- `uv lock` detect if it is uv project
- `uv sync` create venv from uv.lock
- `uv python find --managed-python -v`

## bakefile level

- `uv python find --managed-python --script bakefile.py -v` to detect if there is PEP 723 metadata tag
- find if `bakefile.py.lock` exist
- `uv lock --script bakefile.py`
- `uv sync --script bakefile.py` ensure venv for this file is created

## test with.

1. empty repo (any language repo)
2. repo with empty pyproject.toml (pyproject.toml that invalid for uv)
3. repo with valid pyproject.toml for uv (from uv init)

## each test

1. start the repo
2. init bakefile
3. detect python for the init bakefile
4. re-detect python for the init bakefile and verify it is the same

## Note

- run bake from know python

```
.venv/bin/python -m bake.cli.bake --help
```

---

## Implementation

See `.dev/archive/05-find-python/` for the completed implementation of the `find_python` functionality.
