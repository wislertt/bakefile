# Context

## Key files

- `src/bake/ui/run/main.py` — all fixes land here
    - `main.py:548` `_prepare_subprocess_env` (COLUMNS/LINES freeze — pipe-path resize gap)
    - `main.py:514` `_clean_captured_pty_output`, `main.py:527` `_process_stream_output` (decode site for demo4)
    - `main.py:~600` `_setup_pty_stream` (masters + slaves, ctty preexec)
    - `main.py:~670` `_run_with_split` (drain giveup for demo3 lives in splitter finalize path)
    - `main.py:~867` `_run_without_split` (pipe decode site for demo4)
- `src/bake/ui/run/splitter.py` — OutputSplitter tee threads + `finalize()` (demo3 drain giveup, demo5 read loop)
- `bakefile.py` — demo suite `demo1`-`demo13` (`bake demoN` reproduces each; demo13 = pipe-path resize gap)
- `tests/unit/bake/ui/run/test_run.py` — run() test home (TestPtyCaptureCleanup, TestTimeout, TestPtyCtty patterns)

## How run() modes work (carried from 01)

`stream and capture_output` → `_run_with_split` → PTY pair + splitter tee
threads + `_sigwinch_forwarder` (winsize ioctl + killpg SIGWINCH, no ctty).
Stream-only / capture-only → `_run_without_split` → pipes,
`start_new_session=True`, stdout inherited when not capturing. Capture
semantics: cleaned final screen state unless `clean_capture_output=False`
(byte-faithful).

## Drain behavior (demo3, FIXED)

`_drain_pty` drains to EOF (macOS: b"" read; Linux: EIO) bounded by
`drain_timeout` (default 10s, None = forever, threaded through run() +
wrappers). Two drain bugs fixed along the way: `_try_immediate_read` leaked
O_NONBLOCK on EAGAIN (drain misread EAGAIN as EOF), and `_handle_timeout`'s
direct probe could block past the deadline (now only probes when select is
unusable).

## ctty REMOVED (task 1 pivot)

macOS kernel hangs up the whole PTY the moment the ctty session leader
exits — grandchild late output becomes impossible even with drain fixed
(Linux does not do this). Resolution: `_setup_pty_stream` no longer calls
TIOCSCTTY; `_sigwinch_forwarder(master_fds, proc)` instead refreshes master
winsize AND `os.killpg(-proc.pid, SIGWINCH)`. Cost: children have no true
controlling terminal (job control inside child TUIs degrades). start_new_session
kept (tree-kill + killpg target). TestPtyNoCtty pins the no-ctty contract.

## Decode (demo4, FIXED)

Both paths decode via public `decode_errors: DecodeErrors = "replace"`
param (default pins old U+FFFD behavior, logging stays safe).
`DecodeErrors` Literal in main.py: strict/ignore/replace/backslashreplace/
surrogateescape/surrogatepass (custom codecs.register_error names out of
scope). Name avoids collision with command-failure "errors", deviates from
stdlib `errors=` deliberately (user call). `decode_errors="surrogateescape"`
opts into byte-faithful capture: round-trip with
`.encode("utf-8", "surrogateescape")`. Threaded through run()/run_script/
run_uv/ctx.run/ctx.run_script. TestDecodeErrorsParameter covers every
Literal value (handler semantics + raising handlers + drift guard via
`get_args(DecodeErrors) == TESTED_HANDLERS`) on both paths.

## Throughput (demo5, ACCEPTED COST)

Verdict: transport-bound, tuning plateau. `bake demo5` now benches 16MB,
3 reps, median, temp-file sink. Numbers (this machine, macOS):

- bake PTY stream+capture: ~40 MB/s, pipe subprocess ~370 MB/s → ~8.5x
- raw openpty + blocking os.read (no bake code): 74 MB/s — the kernel
  line-discipline ceiling, ~3.9x pipe. Target <=1.5x unreachable by tuning.
- bake-shape loop (fcntl pair + poll per chunk) hits 67 MB/s of that 74 —
  loop overhead ~8%, not the bottleneck. Post-processing (join/decode/ansi
  clean over 16MB) ~15ms total. Remaining bake gap vs raw = tee write-through
    - thread machinery, per-byte cost.

Experiments (both reverted — no measurable win, transport dominates):

- read chunk 4096 → 64k: 9.77x vs 8.89x baseline (noise). tty line
  discipline delivers ~4KB per read regardless of ask. Kept the
  `_READ_CHUNK` constant in splitter.py documenting the knob.
- boundary flush batching (drop per-chunk flush, flush at EAGAIN/EOF):
  9.58x (noise). Writes already coalesce via BufferedWriter 8KB buffer
  sizing against the 4KB arrival rate; per-chunk flush not the cost.

## Gotchas (carried from 01)

- Child code strings in bakefile.py are raw strings (`r"""`) — `\r`/`\x1b`
  otherwise interpreted at bakefile parse time.
- Demos must run via `@bakebook.command()` functions.
- typeshed types `TimeoutExpired.stderr` as `bytes | None` — one
  `# ty: ignore[invalid-assignment]` precedent at the attach site.
- Reading a PTY master after all slaves close raises `OSError(EIO)` on POSIX —
  the EOF signal for demo3 drain.
- `run_script`/`run_uv`/`ctx.run` wrappers must expose any new run() param
  (TestSignatureCompatibility contract).
- ARG lint: unused params need explicit `_ = param` discard.
