# Plan: run() backlog fixes (demo3, demo4, demo5, demo13)

Continues `.dev/active/01-run-fixes/` (tasks 1-6 done). This plan fixes the
deferred run() defects, still verified reproducible via `bake demo3/4/5/13`.

## demo3: grandchild tail lost

**Problem:** splitter threads stop draining the PTY masters ~0.8s after the main
proc exits. A grandchild holding the slave and writing later is never captured.
Plain subprocess waits for pipe EOF and captures it.

**Approach:** after `proc.wait()` returns, keep reading masters until EOF/EIO
(all slave fds closed) instead of a fixed giveup. EOF on the master raises
`OSError(EIO)` once no slave fds remain — that is the natural stop signal.

**Decision gate:** unbounded drain matches subprocess semantics but a runaway
daemon child would hang bake forever. Proposal: drain until EOF with a cap
(default ~10s) and a `drain_timeout` param to opt into `None` (= wait forever,
subprocess parity). Confirm before implementing.

## demo4: lossy decode

**Problem:** capture decodes with `errors="replace"` — invalid UTF-8 becomes
U+FFFD, silent data loss. Plain subprocess returns raw bytes.

**Approach:** bake's capture API is str, so the honest fix is caller control:
thread an `errors` param through `run()` (default `"replace"`, unchanged
behavior) so byte-exact consumers can pass `"surrogateescape"` and round-trip
via `.encode("utf-8", "surrogateescape")`. Split path decodes in
`_process_stream_output`, pipe path in `_run_without_split` — both get it.

**Decision gate:** alternative is switching the default to `"surrogateescape"`
(lossless always, but every str consumer sees `\udcXX` surrogates instead of
U+FFFD — assert-heavy tests may shift). Default-stay + param is the safe pick.

## demo5: PTY backpressure (~4x slower than pipe)

**Problem:** stream+capture through a PTY pair runs ~4x slower than pipes.

**Approach:** measure first, then tune. Suspects, in order:

1. Splitter read chunk size (currently 4096) vs PTY line-discipline buffer
2. Per-chunk terminal write-through (one syscall + GIL hop per small read)
3. Waking both tee threads per chunk

Tasks: bench harness (pipe vs PTY, MB/s), then chunk-size + write-batching
experiments. Target: <=1.5x pipe time. If tuning plateaus above target, accept
and document (PTY honesty costs throughput) — do not switch default transport.

## demo13: pipe-path resize gap (stream-only commands)

**Problem:** stream-only commands (`bake test` shape: `stream=True`,
`capture_output=False`) inherit the tty but never see resizes. Two causes:
`COLUMNS` baked into the env at spawn (shadows ioctl in
`shutil.get_terminal_size`), and `start_new_session=True` detaching the child
from the foreground process group so the kernel never delivers SIGWINCH.
Reproduced by `bake demo13`.

**Approach:** keep `start_new_session` (it guards the Ctrl-C/tree-kill design),
fix around it:

1. `_prepare_subprocess_env`: inject `COLUMNS`/`LINES` only when parent stdout
   is not a tty — children that inherit a real tty ioctl the live size.
2. Pipe variant of `_sigwinch_forwarder`: parent SIGWINCH handler does
   `os.killpg(-proc.pid, SIGWINCH)` (child is session leader, pgid == pid —
   whole tree gets it, matching kernel fg-pgrp delivery). Children without a
   handler ignore SIGWINCH by default, so non-reactive children are unaffected.
   Same guards as the existing forwarder: POSIX, SIGWINCH exists, main thread.

**Testing:** no real terminal in pytest — the test process sends SIGWINCH to
itself (where run()'s handler lives) from a thread while the child counts
signals. Pattern exists in the TestPtyCtty resize harness.

## Out of scope (noted, not planned)

- demo6 remainder (forced ANSI through pipes in CI), stdin `input=`,
  Windows PTY parity, SIGTSTP hang.
