# Console stream routing — Context

Quick-resume file. Read this first when picking the task back up.

---

## SESSION PROGRESS (2026-08-14)

### ✅ COMPLETED (analysis / diagnosis)

- Root cause verified with a live repro (see Evidence).
- Fix design agreed: opt-in `stderr: bool` param on `console` message functions
  (follows rich convention; default = each function's natural pipe).
- `plan.md` written.
- `data-kit` side has a **TODO** marking the call site to update once bake ships
  (`src/abc_data_kit/bakelib/terragrunt_space.py`, `_report_action_required`).

### ✅ DONE (bake-side, 2026-08-14)

- **Phase 1** — `console.py`: added `_get_console(stderr)` + `_print_prefix(target, ...)`;
  collapsed `prefix_out`/`prefix_err` bodies to delegate to `_print_prefix` (kept as public
  thin wrappers — still tested). Added keyword-only `stderr: bool` (natural default per fn:
  `echo`=False, rest=True) to `echo`, `success`, `info`, `start`, `end`, `cmd`, `warning`,
  `error`; threaded through `start`/`end`→`info`. `warning`/`error` GHA branch now uses the
  chosen console too. `uv run ruff check` + `uv run ty check` + import smoke clean.
- **Phase 2** — `test_console.py`: added `TestStderrOverride` (8 funcs, override flips pipe)
    - `TestStderrOverrideGitHubActions` (`::error::`/`::warning::` on chosen fd). 755 ui tests
      pass; existing default-behavior tests stay green.

### 🟡 IN PROGRESS

- **Phase 3** — needs: bake git tag (release; outward-facing, awaiting developer) + data-kit
  dep bump + wire `_report_action_required` (`console.error(msg, stderr=False)`) and drop the
  temp `console.flush()`. data-kit is a separate repo — done there, not here.

### ⚠️ BLOCKERS / DEPENDENCIES

- Needs bake release + `data-kit` dep bump before the downstream bug is actually
  closed. Until then `data-kit` keeps a temporary `console.flush()` (hygiene only,
  does **not** fix ordering).

---

## The bug (one paragraph)

`data-kit` `TerragruntSpace.apply()` streams `terragrunt run --all apply`
(stdout dump) then emits an `[ACTION REQUIRED]` verdict via `console.error`
(stderr). In GitHub Actions the verdict renders **inside** the dump. Cause: GHA
reads stdout and stderr with two independent readers and merges by arrival; the
large stdout dump is still draining when the one stderr line lands. Local is fine
(TTY = single consumer). **Only emitting the verdict on the same pipe as the dump
(stdout) guarantees order.** flush/wait/sleep can't fix it — the race is inside
GHA's readers, not Python.

---

## Evidence (verified)

1. **Terragrunt fd mapping** — minimal `null_resource` stack,
   `terragrunt run --all plan` split to files:
    - `STDOUT`-tagged output (resource dump, `Plan:` line) → **stdout**.
    - `INFO` lines (init, provider download) → **stderr**, temporally _before_ the dump.
2. **bake streaming** — `ctx.run(capture_output=True)` (default `stream=True`) →
   `_run_with_split` → PTY on Unix (`run/main.py:602`). `OutputSplitter._handle_data`
   writes raw bytes via `target.buffer.write(data); target.buffer.flush()` per chunk
   (`run/splitter.py:43-48`); `sys.stdout` for the stdout PTY, `sys.stderr` for the
   stderr PTY (`run/splitter.py:216,236`). `finalize()` joins reader threads
   (`run/splitter.py:254`) → all bytes flushed before `ctx.run` returns.
3. **console.error/warning** — GHA mode emits `::error::` / `::warning::` to the
   `err` console = **stderr** (`console.py:225-242`). Hardcoded to `err`.
4. **console.flush()** — flushes `out.file` + `err.file` (`console.py:245-247`).
   Splitter already flushes per chunk → calling it here is a no-op for ordering.

---

## Key files

### bake (this repo — to change)

- **`src/bake/ui/console.py`** — add `_get_console(stderr: bool) -> Console` helper;
  add `*, stderr: bool = <natural>` (`False` for `echo`, `True` for the rest) to
  `echo`, `success`, `info`, `start`, `end`, `cmd`, `warning`, `error`. Collapse
  `prefix_out`/`prefix_err` → `_print_prefix`. Skip structural
  `line`/`thin_line`/`block`/`script_block`.
- **`tests/unit/bake/ui/test_console.py`** — default unchanged + explicit `stderr`
  override routing per function (`stderr=False`→stdout on stderr-default funcs,
  `stderr=True`→stderr on `echo`); GHA-mode `::error::`/`::warning::` on chosen fd.

### data-kit (consumer — update after bake release)

- **`src/abc_data_kit/bakelib/terragrunt_space.py`** —
  `TerragruntSpace._report_action_required` (around the `console.error` /
  `console.warning` block). Has a **TODO**; switch to
  `console.error(msg, stderr=False)` / `console.warning(msg, stderr=False)` and
  drop the temp `console.flush()`.

---

## Key decisions (locked)

1. **Param = `stderr: bool`**, default = each function's natural pipe (`True` for
   the error-family, `False` for `echo`). Follows `rich.Console(stderr=)` /
   `click.echo(err=)`. Rejected `stream: Literal[...] | None` (bespoke, no
   precedent) and `stdout: bool` (plan history). Bool is authoritative — no
   `None` sentinel.
2. **Opt-in, default preserves behavior.** No silent global change.
3. **Cover all message functions**, not just `error`/`warning` — the race is
   general (any message on pipe X after a dump on pipe Y). Structural framing
   helpers excluded for now.
4. **GHA workflow commands stay.** `::error::` / `::warning::` are honored on
   both stdout and stderr by GitHub.
5. **No arbitrary `Console` injection.** Only two real pipes; a string pick suffices.

---

## Quick resume

1. Read `plan.md` (design + phases).
2. Implement Phase 1 in `src/bake/ui/console.py`.
3. Add tests (Phase 2).
4. Release bake, bump `data-kit` dep, wire the call site (Phase 3) — remove the
   `data-kit` TODO + temp `console.flush()`.
5. Confirm via the next GHA `bake apply`: marker renders after the dump.
