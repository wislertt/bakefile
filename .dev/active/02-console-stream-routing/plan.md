# Console stream routing — Implementation Plan

Status: **Phase 1+2 DONE** (bake-side, 2026-08-14). Phase 3 pending: bake git tag
(release; awaiting developer) + data-kit dep bump + wire call site. See `context.md`.

---

## Executive summary

Add an opt-in `stderr: bool` parameter to `console` message functions so a caller
can emit a message on **stdout** or **stderr** regardless of the function's
default. Unblocks a real downstream bug: in GitHub Actions, a post-run verdict
emitted on stderr (e.g. `console.error`) lands **mid-stream** when a command just
dumped a large output to stdout, because GHA merges the two pipes by arrival
time.

The `stderr` default matches each function's natural pipe (`True` for the
error-family, `False` for `echo`) = current behavior, zero change unless a caller
overrides.

---

## Problem (why)

Downstream bug (tracked in `data-kit`): `TerragruntSpace.apply()` runs
`terragrunt run --all apply` (captured + streamed), then emits an
`[ACTION REQUIRED]` verdict via `console.error`. In GHA the verdict renders
inside the terragrunt output dump instead of after it.

Root cause (verified — see `context.md`):

- `terragrunt run --all` writes its `STDOUT`-tagged output dump to **stdout** (fd 1).
- `console.error` writes `::error::…` to **stderr** (fd 2).
- GHA drains fd 1 and fd 2 with **two independent readers** and merges by arrival.
  The dump (fd 1, large) is still draining when the single stderr line (fd 2)
  arrives → the marker is inserted mid-dump.
- **Local is unaffected** (TTY: both fds → one terminal, write-time order kept).

Why flush / wait / sleep cannot fix it: `ctx.run` already joins the reader
threads and flushes per chunk before returning (`run/splitter.py`); Python's side
is done. The race is inside GHA's two readers — unreachable from Python.

**Only same-pipe guarantees order** (one pipe → one reader → write order kept).

---

## Design

### Parameter: `stderr: bool` (follows rich)

Matches `rich.Console(stderr=)` and `click.echo(err=)` — bool is authoritative,
it fully determines the pipe. The default is each function's natural destination
(`True` = stderr for the error-family, `False` = stdout for `echo`), so the
default preserves current behavior. No `None` sentinel: bool always wins.

| call                       | result                    |
| -------------------------- | ------------------------- |
| `error(msg)`               | stderr (`stderr=True`)    |
| `error(msg, stderr=False)` | → stdout (fixes the race) |
| `echo(msg)`                | stdout (`stderr=False`)   |
| `echo(msg, stderr=True)`   | → stderr                  |

Rejected `stream: Literal["stdout","stderr"] | None`: bespoke, no industry
precedent (rich/click/Python `print(file=)` all use bool or object, not a string
pipe picker). `stderr: bool` reuses the familiar rich convention. No arbitrary
`Console` injection (over-engineering — only two pipes exist).

### Helpers

```python
def _get_console(stderr: bool) -> Console:
    return err if stderr else out


def _print_prefix(
    target: Console, *, emoji: str | None, label: str, style: str, message: str, **kwargs
) -> None:
    target.print(
        _format_prefix(target, emoji=emoji, label=label, style=style, message=message), **kwargs
    )
```

`_format_prefix` already takes the console object (`console.py:96`), so it works
for either target. `prefix_out` / `prefix_err` collapse into `_print_prefix`.

### Scope — which functions get `stderr`

| Function                                        | Default | `stderr` default | Notes                                                                             |
| ----------------------------------------------- | ------- | ---------------- | --------------------------------------------------------------------------------- |
| `echo`                                          | stdout  | `False`          | cover the "echo → stderr" case                                                    |
| `success`                                       | stderr  | `True`           | verdict, can follow a dump                                                        |
| `info`                                          | stderr  | `True`           | generic, may follow a dump                                                        |
| `start`                                         | stderr  | `True`           | forwards to `info`                                                                |
| `end`                                           | stderr  | `True`           | forwards to `info`                                                                |
| `cmd`                                           | stderr  | `True`           |                                                                                   |
| `warning`                                       | stderr  | `True`           | GHA `::warning::` honored on either pipe                                          |
| `error`                                         | stderr  | `True`           | GHA `::error::` honored on either pipe                                            |
| `line` / `thin_line` / `block` / `script_block` | stderr  | ❌               | structural framing, not ordering-sensitive verdicts. Add later if a case appears. |

GHA workflow commands (`::error::`, `::warning::`) are honored by GitHub on
**both** stdout and stderr, so routing them to stdout keeps the annotation.

### Functional change for `error` / `warning`

```python
def warning(message: str, *, stderr: bool = True, **kwargs) -> None:
    t = _get_console(stderr)
    if bake_settings.github_actions:
        t.print(f"::warning::{message}", **kwargs)
    else:
        _print_prefix(
            t,
            emoji=":warning-emoji: ",
            label="WARNING",
            style="bold yellow",
            message=message,
            **kwargs,
        )


def error(message: str, *, stderr: bool = True, **kwargs) -> None:
    t = _get_console(stderr)
    if bake_settings.github_actions:
        t.print(f"::error::{message}", **kwargs)
    else:
        _print_prefix(t, emoji=":x:", label="ERROR", style="bold red", message=message, **kwargs)
```

---

## Implementation phases

### Phase 1 — `console.py` core

- Add `_get_console(stderr: bool) -> Console` helper.
- Collapse `prefix_out` / `prefix_err` → `_print_prefix` (keep `prefix_out` /
  `prefix_err` as thin wrappers if any caller uses them directly; grep first).
- Add `*, stderr: bool = <natural>` to: `echo` (`False`), `success`, `info`,
  `start`, `end`, `cmd`, `warning`, `error` (all `True`). Thread through
  forwarders (`start`/`end`/`success` → `info`/`prefix_err`).
- **Verify**: `uv run ruff check src/bake/ui/`, `uv run ty check`, import smoke.

### Phase 2 — Tests (`tests/unit/bake/ui/test_console.py`)

For each `stderr`-enabled function:

- default unchanged (stdout funcs → stdout, stderr funcs → stderr).
- override routes to the other fd: `stderr=False` on stderr-default funcs →
  stdout; `stderr=True` on `echo` → stderr (assert via
  `capsys.readouterr().out` vs `.err`).
- `error`/`warning`: GHA mode (`monkeypatch bake_settings.github_actions = True`)
  emits `::error::` / `::warning::` on the chosen fd.

Existing tests must stay green (behavior unchanged at default).

### Phase 3 — Release + downstream wiring

- Bump bake version, release, update `data-kit` dep pin.
- `data-kit` `TerragruntSpace._report_action_required`:
  `console.error(msg, stderr=False)` / `console.warning(msg, stderr=False)`,
  drop the temporary `console.flush()`.
- **Verify end-to-end**: next GHA run of `bake apply` — marker logs after the dump.

---

## Risk assessment

- **Behavior change**: none at default (`stderr` = each function's natural pipe).
  Pure opt-in.
- **API surface**: keyword-only `stderr` added to 8 functions; no positional
  breakage. Existing `**kwargs` forwarded unchanged.
- **GHA annotations**: workflow commands valid on both streams — verified.
- **Coverage gap**: structural funcs (`block` etc.) excluded by design; documented.

## Success metric

In GHA, `console.error(msg, stderr=False)` after a streamed stdout dump
renders **after** the dump, not inside it. Local output unchanged.
