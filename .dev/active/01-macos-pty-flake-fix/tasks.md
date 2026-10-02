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
- [ ] Push branch, CI repro workflow green x3 consecutive (BLOCKED: needs user commit first, no auto-commit policy)
- [ ] Cleanup: pty_trace.py, conftest gate, stress file, workflow,
      probe files in /tmp/flake_loop
- [ ] Decide decorator removal with user (separate commit)
- [ ] Update this file + context.md after every step
