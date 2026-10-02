# Tasks: macOS PTY empty-capture flake fix

## Done

- [x] CI repro harness + instrumented trace (branch ci/pty-flake-repro)
- [x] Root cause proven: any wait syscall on child discards unread macOS
      PTY master data; no-wait data survives ~0.65s then decays
- [x] Failing acceptance test added:
      test_pty_capture_survives_reader_starvation (TDD red)
- [x] rescue_pending() added to OutputSplitter (keep)
- [x] Docs created (.dev/active/01-macos-pty-flake-fix/)

## In progress

- [x] Exit detection without reap (subagent, 13 probes): sysctl
      kinfo_proc P_WEXIT poll wins. kqueue + zombie check disqualified
      (both fire after data destroyed, XNU defers session-leader exit
      ~0.6s). Validated 50/50 idle + 50/50 loaded + SIGKILL + timeout.

## Todo

- [x] Replace broken waitid _wait_no_reap body in main.py (sysctl poll, darwin-only)
- [x] Acceptance test green (unset CI, local)
- [x] Full unit suite green locally (2365 passed, 44.7s)
- [x] bake lint clean (ruff + format + ty on changed files)
- [ ] Push branch, CI x10 round 2 (round 1 = 5/10 fail, reader poll root cause found + fixed)
- [x] Round 2 (run 36948258173): 2365/2366, zero empty-capture, py3.10
      mock bug only -> fixed in 49bc692
- [x] Round 3 (run 36949127007): 5/10 fail. Mechanism A fixed (trace:
      no poll, reader first read at +647ms). Mechanism B remains: 0.65s
      kernel decay timer vs starved reads on 3-vCPU runner. Options
      with user: session-leader probe / main-thread pump / mitigate
- [ ] User decision: probe removing session-leader (setpgid, same session)
- [x] Probe C done (FINAL): session theory dead. Decay fires on last
      slave fd close, not session-leader exit. Child never had ctty
      (TTY=?? in all variants, no TIOCSCTTY from subprocess)
- [x] Slave-hold fix implemented (main.py): parent keeps slave fds,
      releases after rescue_pending / before finalize, idempotent
      (try + except + finally). 169 targeted pass, full suite 2366
      pass, lint clean, no fd leak
- [ ] User commit + push, CI x10 round 4 decides decorators
- [x] Round 4 (run 36956751211, commit 2603fe0): 10/10 GREEN. Fix
      proven. All 3 mechanisms closed
- [ ] Follow-up commit: remove 17 commented decorators + commented
      imports (3 test files). Keep 2 ACTIVE decorators (unrelated)
- [ ] Cleanup: pty_trace.py, conftest gate, stress file, workflow,
      /tmp/flake_loop probes
- [ ] User review, then merge decision (no merge without approval)
- [ ] Cleanup: pty_trace.py, conftest gate, stress file, workflow,
      probe files in /tmp/flake_loop
- [ ] Decide decorator removal with user (separate commit)
- [ ] Update this file + context.md after every step
