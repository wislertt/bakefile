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
threads + ctty + `_sigwinch_forwarder`. Stream-only / capture-only →
`_run_without_split` → pipes, `start_new_session=True`, stdout inherited when
not capturing. Capture semantics: cleaned final screen state unless
`clean_capture_output=False` (byte-faithful).

## Drain behavior today (demo3)

Splitter threads keep reading masters after proc exit but give up after a
~0.8s window (see `splitter.py` finalize / drain loop). Grandchild writing
later than that is dropped from both stream and capture.

## Decode today (demo4)

Both paths decode with `errors="replace"`. Split path also does `\r\n` → `\n`
normalize + optional `_clean_captured_pty_output`. `clean_capture_output=False`
gives raw PTY bytes-as-str but still replace-decoded.

## Throughput today (demo5)

`bake demo5` shows PTY path ~4x pipe. Chunk size and write batching unmeasured.
Write the bench BEFORE any tuning change so numbers compare.

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
