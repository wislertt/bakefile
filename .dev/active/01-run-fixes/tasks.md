# Tasks

Before-outputs captured 2026-08-29 (`bake demoN > file 2>&1`, parent not a tty).

## Task 1: Fix overload type lie (demo7)

Before:

```
===== overload declares stdout: str when capture_output omitted, runtime gives None =====
runtime stdout: None (declared str at main.py:194)

===== probe with ty: omitted arg passes bad annotation, explicit fails =====
probe A_omitted: accepted (type lie)
probe B_explicit_false: rejected (honest)
```

- [x] 1.1 Change first overload (`main.py:194`): `capture_output: Literal[True] = True` → `capture_output: Literal[True]` (drop the default). Second overload keeps `Literal[False]` + `= False` default, so omitted arg resolves to `CompletedProcess[None]`
- [x] 1.2 Run `uv run ty check` across repo, fix any caller that omitted `capture_output` and used `.stdout`/`.stderr` as `str` (the lie was hiding these) — no callers relied on the lie, ty clean
- [x] 1.3 Add/adjust unit test covering both overloads resolve correctly — added `test_run_capture_omitted_returns_none_stdout_stderr` in tests/unit/bake/ui/run/test_run.py
- [x] 1.4 Verify: `bake demo7` → `probe A_omitted: rejected (honest)`, runtime stdout still `None` ✓ (2026-08-29)

## Task 2: Fix PTY fd leak on failed spawn (demo10)

Before:

```
===== bake: failed spawn leaks PTY fds (no try/finally around openpty) =====
fds: 4 -> 16 (delta 12)

===== successful runs close everything =====
fds: 16 -> 16 (delta 0)
```

- [x] 2.1 Wrap `Popen` in `_setup_pty_stream` (`main.py:555-564`) with try/except that closes `stdout_fd`/`stderr_fd` + slaves, then re-raises
- [x] 2.2 Unit test (POSIX only, skipif win32): run nonexistent command 3× via `run(..., capture_output=True)`, assert fd count stable — `test_run_failed_spawn_does_not_leak_pty_fds`
- [x] 2.3 Verify: `bake demo10` → both sections `FIXED: ... leak no fds (delta 0)` ✓ (2026-08-29)

## Task 3: Respect NO_COLOR before injecting color forcing (demo11)

Before:

```
===== user sets NO_COLOR=1: bake still injects FORCE_COLOR, child colors anyway =====
captured: '\x1b[31mCOLORED\x1b[0m\n'

===== plain subprocess honors NO_COLOR =====
captured: b'PLAIN\n'
```

- [x] 3.1 In `_prepare_subprocess_env` (`main.py:518-519`): after merging user env, skip `FORCE_COLOR`/`CLICOLOR_FORCE` setdefault when `NO_COLOR` present (non-empty, per no-color.org)
- [x] 3.2 Unit test: `run(..., env={"NO_COLOR": "1"})` → child sees no `FORCE_COLOR`; without NO_COLOR → still injected — TDD: `test_no_color_suppresses_color_forcing` written first, confirmed red, then green. Note: autouse `disable_colors` fixture sets NO_COLOR for every test, so `test_terminal_size_oserror_fallback` needed `monkeypatch.delenv("NO_COLOR")` to still see injection
- [x] 3.3 Verify: `bake demo11` → `captured: 'PLAIN\n'` + `FIXED: NO_COLOR beats injected FORCE_COLOR` ✓ (2026-08-29)

## Task 4: Set PTY winsize + forward SIGWINCH (demo1, demo2)

Before (demo2 section 1, PTY tee):

```
[child] isatty=True ioctl_winsize=0x0 fallback=80x24
captured: '[child] isatty=True ioctl_winsize=0x0 fallback=80x24\n\r[##                  ] 10%\r[####                ] 20%...'
```

Before (demo1 section 1): child draws 110 cols into 80-col view, `\x1b[3A`
cursor-up lands on wrong rows every frame (garble in both stream+capture and
stream-only when parent tty is 80 cols).

- [x] 4.1 After `pty.openpty()` (`main.py:548,552`): read parent terminal winsize (`fcntl.ioctl` `TIOCGWINSZ` on stdout/stderr/0), `TIOCSWINSZ` it onto both PTY masters. Parent not a tty → fall back to `COLUMNS`/`LINES` env or `shutil.get_terminal_size()`, never leave `0x0` — `_get_parent_terminal_size()` + `_set_pty_winsize()` helpers; GOTCHA: struct winsize order is `(ws_row, ws_col, ...)`, first swap shipped `24x80` before fix
- [x] 4.2 Forward SIGWINCH: while proc alive, handler reads new parent winsize and sets it on both masters. Unregister handler after wait. POSIX only (path already non-win32) — `_sigwinch_forwarder(master_fds)` ctx manager in `_run_with_split`, restores previous handler; `StreamSetup` gained `master_fds`
- [x] 4.3 Unit test: mock ioctl, assert `TIOCSWINSZ` called with parent size; parent-not-a-tty fallback path — TDD: `TestPtyWinsize` (2 tests) written first, both RED (`0x0`), then green. Only `fcntl.ioctl` faked (splitter uses `fcntl.fcntl`); `TIOCSWINSZ` passes through to real kernel so child reads actual PTY state
- [x] 4.4 Verify: `bake demo2` → child reports `ioctl_winsize=<real size>` (e.g. `120x30`), not `0x0`; `bake demo1` honest child draws clean at real width — demo2 section 1 `ioctl_winsize=80x24` (fallback size, parent piped) + FIXED verdict; demo1 raw ws_col=80 + FIXED verdict ✓ (2026-08-29). demo1 reworked same day: bake modes now run the honest child (clean render), over-drawing child kept only as section 4 no-bake contrast — its garble is a child-side bug bake cannot fix. Mid-run resize proven via /tmp PTY harness (80x24 → 120x30 propagated). Child SIGWINCH delivery fixed same day: `_acquire_ctty_preexec` (TIOCSCTTY on slave after setsid, stdlib pty.fork pattern; darwin `0x20007461`, linux `0x540E`, other POSIX skipped) — harness now shows `RESIZED: 120x30`, demo12 section 1 signals > 0 on resize; user preexec_fn (if passed) still runs after ctty acquisition. `TestPtyCtty::test_pty_child_gets_controlling_terminal` TDD'd red→green
- [x] 4.5 Manual resize check: run `bake demo1` in real terminal, resize window mid-run, redraw stays aligned — verified via `bake demo12` in real terminal 2026-08-29: bar tracked every resize step (145→151 cols) and child received 8 SIGWINCH signals under bake, matching plain subprocess behavior. Automated too: `TestPtyCtty::test_resize_mid_run_delivers_sigwinch_to_child` spawns bake under a test-owned PTY, resizes the master mid-run, asserts child signal count > 0 (~4s); regression-checked by temporarily dropping `_sigwinch_forwarder` → test fails with `signals: 0`. Stabilized 2026-08-29 after real flake: fixed `sleep(1.0)` raced bake import + Popen on slow/cold machines (resize landed before forwarder installed) → now the child prints `child-ready` after installing its handler and the harness resizes only on seeing it

## Task 5: Attach partial output to TimeoutExpired (demo8)

Before:

```
===== bake: TimeoutExpired discards partial output =====
START
exc.stdout: None

===== plain subprocess: TimeoutExpired carries partial output =====
exc.stdout: b'START\n'
```

- [x] 5.1 In `_run_with_split` (`main.py:714-725`): except clause now binds `exc`, keeps single kill/wait/finalize block, then `isinstance(exc, TimeoutExpired)` → `_process_stream_output` (same decode + `\r\n` normalize) → attach `exc.output`/`exc.stderr` (str). KeyboardInterrupt branch unchanged (no attachment, matches subprocess.run). ty: typeshed declares `TimeoutExpired.stderr: bytes | None` → one `# ty: ignore[invalid-assignment]` (repo precedent: bakebook.py:350)
- [x] 5.2 TDD: `test_timeout_expired_carries_partial_stdout` + `test_timeout_expired_carries_partial_stderr` written first, both RED (`exc.stdout`/`exc.stderr` None), then green. Used `assert isinstance(stdout, str)` guard so ty accepts str `in` (typeshed types attrs as bytes). Split path only — pipe path (`_run_without_split` `main.py:846-849`) re-raises communicate's own exc, stdlib already populates partial there
- [x] 5.3 Verify: `bake demo8` → first section `exc.stdout: 'START\n'` ✓ (2026-08-29, str vs plain subprocess `b'START\n'` bytes). Module suite 193 passed, ty/ruff clean

## Task 6: Clean captured PTY output (demo2) — DECISION GATE: B vs C

Before (demo2 section 1, same capture as task 4):

```
captured: '[child] isatty=True ... \n\r[##                  ] 10%\r[####                ] 20%... \r[####################] 100%\nDONE\n'
```

`\r`-redraw frames and ANSI escapes land in `result.stdout` verbatim. Only
`\r\n` → `\n` is normalized today (`main.py:501-505`).

- [x] 6.0 Decided B (post-process capture) 2026-08-29, user confirmed. C rejected: pipes kill the PTY's reason to exist (colors + live animation in stream view). Residual risks accepted + mitigated: partial overwrite `abc\rX` loses `bc` (rare, bars redraw full frame); multi-line `\x1b[nA` redraws still stack frames in capture (backlog); OSC sequences (`\x1b]0;title\x07`) not stripped (capsys regex covers CSI + 2-char only)
- [x] 6.1 [B] `_clean_captured_pty_output` (`main.py:500-511`): `strip_ansi` (reused from `bake.ui.logger.capsys`, no import cycle) then per line keep last NON-empty `\r` segment (empty trailing segment = child cut mid-frame → keep previous). Applied in `_process_stream_output` (`main.py:513`) behind new `pty: bool = False` param; both call sites in `_run_with_split` pass `use_pty` — Windows pipe-split + `_run_without_split` pipe path stay raw (deliberate `\r` preserved)
- [x] 6.2 TDD: `TestPtyCaptureCleanup` (7 tests, test_run.py:477) written first — 5 RED / 2 green-guards (empty, pipe-path guard) → all green. Covers: frame collapse, ANSI+`\r`, mid-line overwrite, no trailing newline, truncated trailing `\r` keeps content, empty, pipe-path NOT collapsed. Edge-pin tests added after fix (pass immediately, pin semantics): partial overwrite `abc\rX` → `X`, stderr frames (tqdm case), timeout partial + truncated frame (task 5 × 6 interaction), ONLCR `\r\r\n` doubling. Also updated 2 pre-task-6 tests (`test_run_stream_preserves_colors_with_pty`, `TestStringCommand::test_preserves_colors_with_pty`) that asserted ANSI in capture — now assert stream view keeps colors + capture clean
- [x] 6.3 Verify: `bake demo2` → `captured: '[child] isatty=True ioctl_winsize=80x24 fallback=80x24\n[####################] 100%\nDONE\n'` ✓ (2026-08-29, exact target)
- [x] 6.4 Rerun demo4 (invalid UTF-8 still `errors="replace"`, cleanup doesn't corrupt) + demo3 (grandchild tail still lost = known backlog, no new regression) + demo8 (partial output still attached, `START\n` has no `\r`) ✓. Module suite 200 passed, ty/ruff clean
- [x] 6.5 (follow-up, 2026-08-29) Full-suite catch: test helper `get_str_from_inline_env` round-tripped literal `\r` through stream+capture → collapsed → fixed by `stream=False` (pipes always raw). Full-suite catch exposed gap: no mode gave live stream + raw capture. Added `clean_capture_output: bool = True` param to `run()` (+ `run_script`, `run_uv` per TestSignatureCompatibility contract, + `_run_with_temp_file`/`_run_with_split` plumbing) — `False` = byte-faithful PTY capture, silent no-op on pipe paths (no error: `False` always satisfied, platform-portable). TDD: 3 tests RED (TypeError) → green; default behavior unchanged (demo2 still cleaned); 207 module tests pass

## Wrap-up

- [ ] 7.1 `bake lint` clean
- [ ] 7.2 `bake test` green
- [ ] 7.3 Full demo sweep `demo1`-`demo11`, confirm each before/after matches expectations in this file
- [ ] 7.4 Decide fate of demo code in bakefile.py (keep as live probes vs strip before commit)
