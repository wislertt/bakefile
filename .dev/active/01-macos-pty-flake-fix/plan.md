# Plan: macOS PTY empty-capture flake fix

Goal: root-cause fix in `src/bake/ui/run` so PTY capture survives reader
starvation + macOS reap-discards. Replace `@flaky_on_macos_ci` mitigation.

## Strategy

Phase A (docs): this folder = durable state across compactions.
Update context.md + tasks.md on EVERY meaningful step.

Phase B (exit detection): find child-exit detection that does NOT reap.

1. Debug kqueue NOTE_EXIT probe (`/tmp/flake_loop/probe7.py`), suspect
   kevent construction bug (event never fired).
2. Fallback: zombie detection without reap. Check if psutil is already a
   dependency (pyproject.toml). If not: ctypes sysctl
   `CTL_KERN/KERN_PROC/KERN_PROC_PID` -> `kinfo_proc.p_stat == SZOMB`
   (what psutil does internally on macOS).
3. Choose simplest reliable option, validate with probe:
   register detection, child exits, data still readable after 0.5s.

Phase C (wire fix): replace broken `_wait_no_reap` waitid body in
`src/bake/ui/run/main.py` with validated detection. Keep
`rescue_pending` + join-then-wait order. Acceptance:
`test_pty_capture_survives_reader_starvation` green.

Phase D (verify): targeted dir tests -> full unit suite -> `bake lint` ->
push to ci/pty-flake-repro branch, run repro workflow several times,
confirm stress+suite green across runs.

Phase E (cleanup): delete temp artifacts (see context.md list), remove
`@flaky_on_macos_ci` decorators IF user agrees (separate commit on main,
user commits). Final summary with root cause explanation.

## Risks

- kqueue may be genuinely unreliable for already-exited children ->
  zombie-check fallback exists.
- Grandchild case (child spawns long-lived grandchild holding slave):
  exit detection must return at CHILD exit, not slave EOF. Zombie check
  and kqueue both satisfy this. Do NOT use master-EOF as exit signal.
- TimeoutExpired parity: exit-detection needs timeout support
  (kqueue control has timeout arg; zombie-check = poll loop + deadline).
