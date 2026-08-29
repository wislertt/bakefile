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

- [x] 2.0 DECISION: default stays `"replace"` + public param (user approved). REVISION: renamed to `decode_errors` with `DecodeErrors` Literal type (user call after discussion)
- [x] 2.1 TDD: test — invalid UTF-8 child output, `decode_errors="surrogateescape"` → capture round-trips via `.encode("utf-8", "surrogateescape")` (RED: no param). Also split-path variant
- [x] 2.2 TDD: test — default unchanged: U+FFFD still appears (pin compat), both paths. ADDED: every Literal value tested (handler semantics, raising handlers, surrogatepass positive case) + get_args drift guard
- [x] 2.3 Fix both decode sites: `_process_stream_output` (split) + `_run_without_split` (pipe)
- [x] 2.4 Thread `decode_errors` through run()/run_script/run_uv/ctx.run/ctx.run_script; TestPopenKwargs EXCLUDED comment for `errors` updated (breaks internal bytes decode)
- [x] 2.5 Verify `bake demo4` → `surrogateescape round-trip == raw bytes: True`
- [x] 2.6 No regression: demo2 (clean capture), demo8 (partial attach), run pkg + context + export tests 580 green, ty clean, ruff clean

## Task 3: PTY throughput tuning (demo5)

- [x] 3.1 Bench harness: pipe vs PTY, MB/s through run() (temp file, repeat 3x, report median). demo5 rewritten: 16MB payload (2MB hid steady state behind startup noise), median of 3, temp-file sink, MB/s + ratio vs 1.5x target
- [x] 3.2 Experiment: splitter read chunk 4096 → 64k → 9.77x vs 8.89x baseline (noise). tty line discipline delivers ~4KB per read regardless of ask
- [x] 3.3 Experiment: batch terminal write-through (drop per-chunk flush, flush at EAGAIN/EOF boundaries) → 9.58x (noise). BufferedWriter already coalesces
- [x] 3.4 Re-bench after each; both reverted per keep-what-helps. Kept only `_READ_CHUNK` constant in splitter.py (zero behavior change). Isolation bench added the missing data: raw openpty+blocking read = 74 MB/s ceiling (~3.9x pipe), bake-shape loop = 67 MB/s (loop overhead ~8%), join/decode/clean ~15ms — transport-bound, not loop-bound
- [x] 3.5 Verdict: plateau — accepted cost documented in context.md (raw PTY kernel ceiling ~3.9x pipe makes <=1.5x unreachable; bake sits ~1.7x above its own ceiling from tee write-through, per-byte). No transport switch
- [x] 3.6 No regression: demo1/demo2 (streaming display + clean capture), test_run.py 137 green, run pkg 222 green, ty clean, ruff clean

## Task 4: Pipe-path resize forwarding (demo13)

- [x] 4.1 TDD: test — child counting SIGWINCH, test process sends SIGWINCH to itself from a thread during `run(..., stream=True, capture_output=False)` → child count > 0 (RED confirmed). TestPipeResizeForwarding in test_run.py
- [x] 4.2 TDD: test — `COLUMNS` not injected into child env when parent stdout is a tty (RED confirmed: mocked get_terminal_size → injects today)
- [x] 4.3 TDD: guard tests — COLUMNS still injected when parent stdout is a pipe; capture path (`stream=False`) unchanged (both RED pre-fix: old code injected only on tty stdout). Updated TestPrepareSubprocessEnv.test_terminal_size_oserror_fallback to pin new fallback contract (80x24 hint when no tty anywhere)
- [x] 4.4 Fix: `_prepare_subprocess_env` gates COLUMNS/LINES on parent stdout not a tty — tty children ioctl live size, pipe children get `_get_parent_terminal_size()` (stdout/stderr/stdin ioctl chain) or shutil fallback
- [x] 4.5 Fix: `_pipe_sigwinch_forwarder` — `os.killpg(-proc.pid, SIGWINCH)` on parent resize, POSIX + main-thread guards, wired into `_run_without_split` stream-only branch (capture_output=False)
- [x] 4.6 Verified `bake demo13` section 1 → `FIXED: stream-only child receives SIGWINCH` (simulated resize: SIGWINCH to bake pid, child winch 0→3). `env=<unset>` + `ioctl=` live need real terminal — interactive check pending user
- [x] 4.7 No regression: `bake demo12` FIXED (3/3 signals via PTY forwarder), test_run.py 141 green, run pkg + cli/common 352 green, ty full-repo clean, ruff clean

## Wrap-up

- [ ] 4.1 `bake lint` clean
- [ ] 4.2 `bake test` green
- [ ] 4.3 Demo sweep demo1-demo12, all expectations hold
