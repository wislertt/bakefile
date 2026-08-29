# Tasks

Before-outputs: run `bake demo3`, `bake demo4`, `bake demo5`, `bake demo13`, save each to a file.

## Task 1: Drain PTY to EOF after proc exit (demo3)

- [x] 1.0 DECISION: cap 10s default + `drain_timeout: float | None` param (None = subprocess parity). MID-TASK PIVOT: dropped ctty (user approved) — macOS kernel hangs up whole PTY at session-leader exit, killing grandchild late output; resize now forwarded via killpg SIGWINCH instead
- [x] 1.1 TDD: test — grandchild writes ~1.5s after child exit → capture includes it
- [x] 1.2 TDD: test — cap behavior: grandchild writing past cap is dropped, run() still returns
- [x] 1.3 Fix in splitter finalize path: read masters until EOF/EIO or deadline; also fixed O_NONBLOCK leak in `_try_immediate_read` (EAGAIN misread as EOF) and blocking probe in `_handle_timeout` (could outlive deadline)
- [x] 1.4 Thread `drain_timeout` through run()/run_script/run_uv/ctx.run (TestSignatureCompatibility)
- [x] 1.5 Verify `bake demo3` → `LATE OUTPUT present in capture: True`
- [x] 1.6 No regression: `bake demo8` (timeout partial still attached), `bake demo9` (SIGINT tree kill still fires), test_run.py 125 green, bake lint clean, demo12 real resize verified by user

## Task 2: Caller-controlled decode errors (demo4)

- [ ] 2.0 DECISION: default stays `"replace"` + `errors` param, or default flips to `"surrogateescape"`? Plan recommends param
- [ ] 2.1 TDD: test — invalid UTF-8 child output, `errors="surrogateescape"` → capture round-trips via `.encode("utf-8", "surrogateescape")` (RED: no param)
- [ ] 2.2 TDD: test — default unchanged: U+FFFD still appears (pin compat)
- [ ] 2.3 Fix both decode sites: `_process_stream_output` (split) + `_run_without_split` (pipe)
- [ ] 2.4 Thread `errors` through run()/run_script/run_uv/ctx.run
- [ ] 2.5 Verify `bake demo4` → surrogate round-trip demo line shows no U+FFFD when opted in
- [ ] 2.6 No regression: demo2 (clean capture), demo8 (partial attach), test_export carriage-return tests green

## Task 3: PTY throughput tuning (demo5)

- [ ] 3.1 Bench harness: pipe vs PTY, MB/s through run() (temp file, repeat 3x, report median)
- [ ] 3.2 Experiment: splitter read chunk 4096 → 64k
- [ ] 3.3 Experiment: batch terminal write-through (accumulate chunk burst, single write)
- [ ] 3.4 Re-bench after each; keep what helps, revert what doesn't
- [ ] 3.5 Verdict: if <=1.5x pipe → done; if plateau → document accepted cost in context.md, no transport switch
- [ ] 3.6 No regression: demo1/demo2 (streaming display + clean capture), test_run.py green

## Task 4: Pipe-path resize forwarding (demo13)

- [ ] 4.1 TDD: test — child counting SIGWINCH, test process sends SIGWINCH to itself from a thread during `run(..., stream=True, capture_output=False)` → child count > 0 (RED: no forwarding on pipe path)
- [ ] 4.2 TDD: test — `COLUMNS` not injected into child env when parent stdout is a tty (RED: always injected today)
- [ ] 4.3 TDD: guard tests — COLUMNS still injected when parent stdout is a pipe; capture path (`stream=False`) unchanged
- [ ] 4.4 Fix: `_prepare_subprocess_env` gates COLUMNS/LINES on parent stdout not a tty
- [ ] 4.5 Fix: pipe `_sigwinch_forwarder` variant — `os.killpg(-proc.pid, SIGWINCH)` on parent resize, POSIX + main-thread guards, wire into `_run_without_split` stream-only branch
- [ ] 4.6 Verify `bake demo13` section 1 → `FIXED: stream-only child receives SIGWINCH`, `env=<unset>`, `ioctl=` live
- [ ] 4.7 No regression: `bake demo12` (PTY path forwarding intact), keyring/conftest-adjacent tests unaffected, test_run.py green

## Wrap-up

- [ ] 4.1 `bake lint` clean
- [ ] 4.2 `bake test` green
- [ ] 4.3 Demo sweep demo1-demo12, all expectations hold
