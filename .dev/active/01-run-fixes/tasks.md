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

- [ ] 4.1 After `pty.openpty()` (`main.py:548,552`): read parent terminal winsize (`fcntl.ioctl` `TIOCGWINSZ` on stdout/stderr/0), `TIOCSWINSZ` it onto both PTY masters. Parent not a tty → fall back to `COLUMNS`/`LINES` env or `shutil.get_terminal_size()`, never leave `0x0`
- [ ] 4.2 Forward SIGWINCH: while proc alive, handler reads new parent winsize and sets it on both masters. Unregister handler after wait. POSIX only (path already non-win32)
- [ ] 4.3 Unit test: mock ioctl, assert `TIOCSWINSZ` called with parent size; parent-not-a-tty fallback path
- [ ] 4.4 Verify: `bake demo2` → child reports `ioctl_winsize=<real size>` (e.g. `120x30`), not `0x0`; `bake demo1` honest child draws clean at real width
- [ ] 4.5 Manual resize check: run `bake demo1` in real terminal, resize window mid-run, redraw stays aligned

## Task 5: Attach partial output to TimeoutExpired (demo8)

Before:

```
===== bake: TimeoutExpired discards partial output =====
START
exc.stdout: None

===== plain subprocess: TimeoutExpired carries partial output =====
exc.stdout: b'START\n'
```

- [ ] 5.1 In `_run_with_split` (`main.py:640-644`): after `finalize`, build partial output (same decode path as `_process_stream_output`), re-raise `TimeoutExpired` with `output=`/`stderr=` populated (str, matching bake's str API — plain subprocess gives bytes, bake gives str)
- [ ] 5.2 Unit test: slow child mocked/splitter stub with partial data, timeout=small, assert `exc.stdout` contains partial text
- [ ] 5.3 Verify: `bake demo8` → first section `exc.stdout: 'START\n'`

## Task 6: Clean captured PTY output (demo2) — DECISION GATE: B vs C

Before (demo2 section 1, same capture as task 4):

```
captured: '[child] isatty=True ... \n\r[##                  ] 10%\r[####                ] 20%... \r[####################] 100%\nDONE\n'
```

`\r`-redraw frames and ANSI escapes land in `result.stdout` verbatim. Only
`\r\n` → `\n` is normalized today (`main.py:501-505`).

- [ ] 6.0 Decide approach (see plan.md decision gates). B preferred
- [ ] 6.1 [B] Add post-processing for PTY-captured text: strip ANSI + collapse `\r` redraws (keep final frame per overwrite run), applied in `_process_stream_output` capture path only — stream passthrough stays byte-faithful
- [ ] 6.2 Unit tests for the collapse: plain `\r` overwrite, `\r` + ANSI colors, `\r\n` mix, no trailing newline, empty capture
- [ ] 6.3 Verify: `bake demo2` → section 1 captured ≈ `'[child] isatty=True ... \n[####################] 100%\nDONE\n'` (final frame only, no ANSI)
- [ ] 6.4 Rerun demo4 (invalid UTF-8) + demo3 (grandchild): confirm no regression from new post-processing

## Wrap-up

- [ ] 7.1 `bake lint` clean
- [ ] 7.2 `bake test` green
- [ ] 7.3 Full demo sweep `demo1`-`demo11`, confirm each before/after matches expectations in this file
- [ ] 7.4 Decide fate of demo code in bakefile.py (keep as live probes vs strip before commit)
