# Fix run() Defects Found by Demo Suite

## Goal

Fix the six high-value defects in `run()` (src/bake/ui/run/main.py) proven by
demos `demo1`-`demo11` in bakefile.py. Each fix is verified by re-running its
demo and comparing against the recorded before-output.

## Scope

In scope (ordered cheap → bigger):

| #   | Issue                                                                            | Demo         | Root cause location            |
| --- | -------------------------------------------------------------------------------- | ------------ | ------------------------------ |
| 1   | Overload type lie: omitted `capture_output` types as `str`, runtime gives `None` | demo7        | `main.py:194` vs `main.py:233` |
| 2   | Failed spawn leaks PTY fds (no try/finally around openpty+Popen)                 | demo10       | `main.py:547-566`              |
| 3   | `NO_COLOR` stomped by injected `FORCE_COLOR`                                     | demo11       | `main.py:518-519`              |
| 4   | PTY winsize never set (`0x0`) + no SIGWINCH forward → garbled multi-line redraw  | demo1, demo2 | `main.py:548`                  |
| 5   | `TimeoutExpired` discards partial output                                         | demo8        | `main.py:640-644`              |
| 6   | Capture pollution: `\r` redraw frames + ANSI land in `result.stdout`             | demo2        | `main.py:501-505`              |

Out of scope (backlog, see context.md): SIGTERM orphans (demo9), SIGINT race
before guard installs, stdin `input=` support, silent splitter thread
exceptions, per-stream encoding on Windows, Windows PTY parity, grandchild
tail loss (demo3), decode fidelity (demo4), backpressure (demo5).

## Decision gates

- **Task 6 approach**: B (post-process capture, keep PTY display) vs C (pipes
  for capture path, lose live animation). B preferred — task 4 keeps stream
  display working, C would regress it. Confirm before implementing.

## Ordering rationale

1-3 are one-liners with no behavior risk. 4 is ~15 lines, fixes the root cause
of the garble class. 5 is small but touches exception flow. 6 is the biggest
(heuristic post-processing + tests) and gated on a decision.

## Verification

Per task: rerun the related demo command, compare to before-output recorded in
tasks.md. Run targeted unit tests during development (see CLAUDE.md). Full
`bake test` + `bake lint` before commit.

Demos live in bakefile.py (`demo1`-`demo11`). Before-outputs below were
captured 2026-08-29 with bake output redirected to a file (COLUMNS unset,
parent not a tty unless noted).
