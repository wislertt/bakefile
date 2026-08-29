# Context

## Key files

- `src/bake/ui/run/main.py` — all fixes land here
    - `main.py:190-227` overloads, `main.py:233` runtime default `capture_output=False`
    - `main.py:495-509` `_process_stream_output` (decode + `\r\n` normalize)
    - `main.py:512-533` `_prepare_subprocess_env` (NO_COLOR gate, FORCE_COLOR, COLUMNS injection)
    - `main.py:540-570` `_get_parent_terminal_size` + `_set_pty_winsize` (task 4)
    - `main.py:572-620` `_setup_pty_stream` (fd-leak guard, winsize set on both masters)
    - `main.py:623-660` `_run_with_split` (`_sigwinch_forwarder` in with-block, timeout path)
    - `main.py:745-770` `_sigwinch_forwarder` ctx manager
    - `StreamSetup` gained `master_fds: tuple[int, ...] = ()` (pipe path leaves default)
- `src/bake/ui/run/splitter.py` — OutputSplitter tee threads
- `src/bake/ui/logger/capsys.py:22` — `strip_ansi` (ANSI regex, reusable for task 6)
- `bakefile.py` — demo suite `demo1`-`demo11` (registered via `@bakebook.command()`)

## How run() modes work

`stream and capture_output` → `_run_with_split` → PTY pair (POSIX) + splitter
threads tee raw bytes to terminal + capture lists. `use_pty = non-win32 and
capture_output` (`main.py:623`). Stream-only / capture-only → pipes.

## Demo ↔ issue map

| Demo   | Issue                                     | In fix scope                                                                                  |
| ------ | ----------------------------------------- | --------------------------------------------------------------------------------------------- |
| demo1  | multi-line redraw garble from winsize lie | yes (task 4, done) — bake modes run honest child now; overdraw child kept as no-bake contrast |
| demo2  | PTY winsize `0x0` + capture pollution     | yes (tasks 4, 6)                                                                              |
| demo3  | grandchild tail lost (~0.8s drain giveup) | no — backlog                                                                                  |
| demo4  | lossy decode errors="replace"             | no — backlog                                                                                  |
| demo5  | PTY backpressure ~4× slower than pipe     | no — backlog                                                                                  |
| demo6  | forced ANSI through pipes (CI)            | partially — task 3 covers NO_COLOR case                                                       |
| demo7  | overload type lie                         | yes (task 1)                                                                                  |
| demo8  | TimeoutExpired drops partial output       | yes (task 5)                                                                                  |
| demo9  | SIGTERM orphans, SIGINT guard works       | no — backlog (plus race before guard installs)                                                |
| demo10 | fd leak on failed spawn                   | yes (task 2)                                                                                  |
| demo11 | NO_COLOR stomped by FORCE_COLOR           | yes (task 3)                                                                                  |

## Decisions

- 2026-08-29: scope = the six ranked fixes only. Backlog items deferred:
  demo3/4/5/9 issues, stdin `input=`, silent splitter thread exceptions,
  per-stream encoding (Windows), Windows PTY parity, SIGTSTP hang,
  spawn-lock contention, `_run_with_temp_file` audit. Child ctty/SIGWINCH
  delivery was backlogged, then fixed 2026-08-29 (`_acquire_ctty_preexec`,
  TIOCSCTTY after setsid).
- Task 6 approach pending user confirm: B (post-process capture) preferred over
  C (pipes, loses live animation in stream view).

## Gotchas

- Demos must run via `@bakebook.command()` functions, not bare functions or
  undecorated methods.
- Child code strings in bakefile.py are raw strings (`r"""`) — `\r`/`\x1b`
  would otherwise be interpreted at bakefile.py parse time.
- Demo before-outputs in tasks.md were captured with bake output redirected
  (parent not a tty, COLUMNS unset) — winsize demos still valid because the
  PTY path is used regardless of parent tty.
- struct winsize byte order is `(ws_row, ws_col, ws_xpixel, ws_ypixel)` — row
  first. Packing col first silently swaps size (child fallback printed `24x80`).
- Fake only `fcntl.ioctl` in tests, never whole fcntl module — splitter needs
  real `fcntl.fcntl` for non-blocking mode. `os.get_terminal_size()` is C-level
  and ignores the Python-level fake.
- SIGWINCH handler must be main-thread only (signal.signal raises ValueError
  otherwise) and restore the previous handler; same pattern as `_sigint_guard`.
