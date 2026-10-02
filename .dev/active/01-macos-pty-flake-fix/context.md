# Context: macOS PTY empty-capture flake fix

## Problem

macOS CI flake: real-subprocess capture tests intermittently get `stdout=''`
while stderr echo intact, exit 0. Affected tests (all decorated with
`@flaky_on_macos_ci()` on main as interim mitigation, commit a777f91):

- `tests/unit/bake/ui/run/test_run.py::test_run_simple_command`
- `tests/unit/bake/cli/bakefile/test_run.py::test_run_with_args`
- `tests/unit/bake/ui/run/test_run.py::test_pty_gets_parent_terminal_size`
- `tests/unit/bake/ui/run/test_run.py::test_stderr_frames_collapse_too`

## ROOT CAUSE (proven with local probes, 2026-10-01)

macOS XNU discards unread PTY master-side data when the parent process
waits on the child. Details:

1. `bake` PTY capture path (`src/bake/ui/run/main.py:_run_with_split`):
   `setup.proc.wait()` reaps the child BEFORE reader threads finish.
2. On macOS, `waitpid` (or ANY wait syscall: `os.waitid` with
   `WNOHANG|WNOWAIT` also triggers it) on the PTY session leader
   tears down the tty and discards master data no reader consumed yet.
3. Reader threads (`OutputSplitter._read_pty`) are usually fast and consume
   data live, so output survives. Under CPU starvation (CI: 3-vCPU runner,
   8 xdist workers) the reader wakes after the reap, reads EOF `b""`
   (macOS gives b"" not EIO), capture = empty.
4. Even WITHOUT any wait, unread data decays ~0.65s after the last slave
   fd closes (deferred kernel discard).
5. Linux unaffected: reap does NOT discard unread master data there.
   Windows unaffected: no PTY path (`use_pty` = POSIX only).
6. Bug exists on ALL macOS (local too), not CI-specific. Local tests pass
   because reader never starved. CI load opens the race window.

### Probe evidence (local Darwin 27, `/tmp/flake_loop/`)

| Probe       | Setup                                               | Result                                                           |
| ----------- | --------------------------------------------------- | ---------------------------------------------------------------- |
| probe2.py   | 1 pty, no wait, read after delay 0.4s / 0.8s        | lost 0/100 / 100/100                                             |
| probe3.py A | parent slave kept open, delay 0.8s                  | lost 0/30                                                        |
| probe3.py B | slave closed, delay 0.8s                            | lost 30/30                                                       |
| probe4.py   | reap-first (waitpid), delay 0.05s                   | lost 40/40                                                       |
| probe4.py   | no reap, delay 0.4s / 0.8s                          | lost 0/40 / 40/40                                                |
| probe6.py   | waitid WNOHANG+WNOWAIT poll loop (even +0.4s later) | lost 30/30                                                       |
| probe7.py   | kqueue NOTE_EXIT early-register                     | exit event fired 0/20 (SUSPECT MY BUG)                           |
| probe8.py   | kqueue NOTE_EXIT, slow child (0.4s), raw event      | fires but at exit+0.60s, data already gone 5/5                   |
| probe9.py   | kqueue NOTE_EXIT latency, 2s child                  | event at exit+0.604s (10/10), marker destroyed at delivery 10/10 |
| probe11.py  | kqueue late registration, no PTY                    | fires immediately 10/10 (but useless, see latency)               |
| probe12.py  | zombie flip timing, nopty vs pty                    | nopty +4ms, pty +0.605s (5/5 each)                               |
| probe13.py  | p_stat/p_flag sampling through pty exit window      | p_stat stays SRUN until +0.63s, P_WEXIT set at +4ms              |

### NEW ROOT-CAUSE DETAIL (probes 8-13, 2026-10-01)

kqueue NOTE_EXIT is NOT buggy usage, it is disqualified:

1. Fires ~0.60s AFTER true child exit (XNU deferred session teardown).
2. PTY master data already destroyed at event delivery (probe9: 10/10
   marker gone despite immediate drain after event).
3. Unreliable for fast-exiting pty children: probe7 config misses 20/20
   even with 2s timeout.

Same 0.6s delay applies to sysctl zombie check alone (p_stat == SZOMB,
probe12): a pty session leader stays p_stat=SRUN for ~0.6s after true
exit. The deferred session/tty teardown both delays the zombie state
AND discards the unread master data. Zombie-only check = useless.

WINNER: `kinfo_proc.p_flag & P_WEXIT` (0x2000). Set within ~5ms of true
exit, while p_stat still SRUN. Pure ctypes sysctl, no wait syscall.

### Mechanism validation (`no_reap_wait.py`, `probe10.py`)

`is_exited(pid)` = sysctl kern.proc.pid -> p_stat==SZOMB OR P_WEXIT.
`wait_for_exit_no_reap(pid, timeout)` polls every 5ms, TimeoutExpired.

- probe10 idle: exit detected 50/50, marker readable after detect+0.5s
  sleep 50/50, detect latency 25-69ms
- probe10 under 8 CPU spinners (CI-like): 50/50 + 50/50, latency
  63-423ms (still under the 0.65s decay window)
- SIGKILL long-lived child: detected 0-6ms after kill(), no reap
  (returncode still None), master readable
- Healthy child timeout path: TimeoutExpired raised, child unharmed
- sysctl semantics on Darwin: gone/reaped pid returns success with
  size=0 (NOT ESRCH). p_stat at offset 36, p_flag at 32, p_pid at 40
  (validated at runtime via p_pid assert). SZOMB=5 per SDK proc.h
- psutil is NOT a project dependency (checked pyproject.toml, uv.lock)

kqueue probe7 mystery partially explained: probe7 0/20 was not a
kevent-construction bug, the same code fires 5/5 with a slow child
(probe8). Fast pty children never deliver the event. Irrelevant now.

Key inference chain:

- Any wait syscall on child = data destroyed immediately (probe4, probe6)
- No wait = data survives >=0.4s, decays ~0.65s (probe2/4)
- kqueue NOTE_EXIT = only remaining no-reap exit-detection candidate,
  current probe7 result looks like a kevent usage bug (event should fire)

### CI trace evidence (branch ci/pty-flake-repro, run 36875861541)

Trace showed failing session: reader thread started 635ms after spawn
(starved), first read `b""` on both master fds, `PROCESS raw_out=0 rc=0`.
Successful sessions: reader starts ~10ms, blocks, gets data before exit.

## Fix design (decided)

In `_run_with_split` PTY path, delay the reap until capture drained:

1. Detect child exit WITHOUT any wait syscall (the crux).
   WINNER (validated): ctypes sysctl kern.proc.pid poll,
   `p_stat == SZOMB or p_flag & P_WEXIT` (see probe evidence below).
    - kqueue NOTE_EXIT IS **NOT** VIABLE (fires at exit+0.6s, data gone,
      unreliable for fast pty children).
    - WAITID WNOWAIT IS **NOT** VIABLE (probe6: also destroys data).
    - Plain zombie check (p_stat only) IS **NOT** VIABLE (delayed 0.6s
      for pty session leaders, probe12).
    - psutil not in project deps, use ctypes.
2. After exit detected: `OutputSplitter.rescue_pending()` drains both
   master fds from the main thread (main is always scheduled, reads
   within the window; kernel queue consumed once = no duplication).
3. `finalize()` joins reader threads (they EOF at slave close).
4. `setup.proc.wait()` LAST (reap, data already safe).
5. Timeout semantics: exit-detection must support timeout ->
   TimeoutExpired (keep parity with subprocess.run).

Non-darwin POSIX can keep plain `wait(timeout=timeout)` (no bug there)
OR share the same path if waitid/kqueue portable enough. Keep it simple:
darwin-only special case acceptable.

## Current uncommitted state (branch ci/pty-flake-repro)

`git status`: 3 modified files, NOT committed:

- `src/bake/ui/run/main.py`: added `_wait_no_reap()` (WAITID VERSION -
  KNOWN BROKEN, to be replaced by kqueue/zombie-check) + rescue call +
  `setup.proc.wait()` after finalize. The waitid body must be replaced.
- `src/bake/ui/run/splitter.py`: added `OutputSplitter.rescue_pending()`
  (keep; docstring may need tweak).
- `tests/unit/bake/ui/run/test_run.py`: added
  `test_pty_capture_survives_reader_starvation` (monkeypatches
  `_read_pty` to sleep 1s, asserts marker captured). Currently FAILS
  (correct TDD red state). This is the acceptance test for the fix.

## Test/verify commands

```sh
unset CI && uv run pytest tests/unit/bake/ui/run/test_run.py::test_pty_capture_survives_reader_starvation -x -q --no-header
unset CI && uv run pytest tests/unit/bake/ui/run/ -q --no-header
bake lint
```

Full suite before commit: `unset CI && uv run pytest tests/unit -q -n auto` (~80s).

## Temporary diagnostic artifacts (delete when done)

- Branch `ci/pty-flake-repro` commits: 7792c1c (harness),
  f8422ae (instrumentation), 722ce1e (run-boundary correlation)
- `tests/utils/pty_trace.py`, conftest PTY_TRACE gate,
  `tests/unit/bake/ui/run/test_pty_flake_stress.py`,
  `.github/workflows/pty-flake-repro.yml`
- CI workflow `pty-flake-repro` (manual dispatch ok)
- Local probe scripts: `/tmp/flake_loop/probe*.py`, `debug_rescue*.py`

## User constraints

- CAVEMAN MODE full (terse replies), no em dashes / semicolons
- NO automatic commits on user branches (diagnostic branch pushes were
  explicitly authorized; final fix commit = user decides)
- Keep this .md updated as work progresses (user requirement for
  compaction resilience)
- Use subagents aggressively to preserve context window
- `@flaky_on_macos_ci` decorators stay on main until fix validated in CI

## Update (2026-10-01, phase B complete)

Validated exit-detection mechanism (subagent, 13 probes):

- **kqueue NOTE_EXIT disqualified.** Correct construction fires 15/15 for slow children but at true-exit +0.60s: XNU defers PTY session-leader exit processing ~0.6s and event delivery + data destruction happen at the same moment (probe9: marker destroyed 10/10 despite immediate drain). Fast-exiting PTY children: event never fires (0/20), no-PTY control fires 10/10.
- **Zombie check (p_stat==SZOMB) disqualified.** Session leader stays SRUN ~0.6s after true exit; flips exactly when data is destroyed (probe12).
- **Winner: sysctl kinfo_proc poll, `p_flag & P_WEXIT` (0x2000)**, fallback `p_stat == SZOMB`. P_WEXIT set ~5ms after true exit inside exit1() (after last userspace write, before data decay). Read-only syscall, no wait, data untouched.
- Validation (probe10): 50/50 idle + 50/50 under 8 CPU spinners, detection latency 25-69ms idle / 63-423ms loaded (decay window ~0.65s, rescue must run immediately after detection). SIGKILL of 30s child detected 0-6ms. Timeout raises TimeoutExpired, child untouched. psutil NOT a dependency (checked pyproject + uv.lock), ctypes is the only stdlib option.
- Darwin quirk: reaped/nonexistent pid = sysctl success with size=0 (not ESRCH). p_pid offset assert guards struct layout.

Wired (uncommitted):

- `main.py`: `_process_is_exiting()` + rewritten `_wait_no_reap` (darwin = sysctl poll 5ms, non-darwin = plain `proc.wait(timeout)`). Imports ctypes/errno, module constants `_libc/_SZOMB/_P_WEXIT` under `sys.platform == "darwin"` guard.
- `splitter.py`: `rescue_pending()` unchanged (keeper).
- `test_run.py::test_pty_capture_survives_reader_starvation`: **GREEN** locally.

Remaining: full run/ suite (in flight), full unit suite, lint, CI repro x3, cleanup.

## Update (2026-10-02, hang bug found + fixed)

- Full suite hung 2h with zero output. Cause: `_process_is_exiting` returned
  False for nonexistent/reaped pids (sysctl size=0 / ESRCH), so
  `_wait_no_reap(timeout=None)` polled forever. Unit tests mock Popen with
  fake pids -> instant infinite loop. Subagent probe10 validated real pids
  only, mocked-pid case untested until suite run.
- Fix: pid gone (size=0 or ESRCH) now returns True (nothing to wait for).
  Safe: child exists once Popen returns, so "gone" = exited or reaped.
- Verified: bogus pid -> True, live pid -> False, no-timeout wait returns
  with rc still None (not reaped), timeout raises with child untouched.
  Acceptance test still green.
- INCIDENT: overnight battery drain was NOT the unsolved fix. 8 CPU spinner
  loops from the stress test leaked (kill missed them), load avg hit 248,
  machine ground all night, background runs timed out. Lesson: spinner
  kill must be verified with ps before ending the task.

## Update (2026-10-02, KI-path restructure)

- Suite failure: test_ctrl_c_with_stream_true_kills_process_tree. Final
  setup.proc.wait() was outside the guard try/except, so KI raised there
  skipped _kill_process_tree. Restructured: rescue_pending + finalize +
  wait() all inside guarded try.
- Test hardened: mock pid 12345 could collide with a live pid (infinite
  poll). Test now patches _wait_no_reap side_effect=KeyboardInterrupt --
  deterministic, no fake-pid sysctl.
- test_run.py 149 passed. ruff + format + ty clean.

## Update (2026-10-02, local verification complete -- STOPPED FOR REVIEW)

- Full unit suite: 2365 passed, 3 xfailed, 44.7s. All lint clean.
- Fix complete and uncommitted on ci/pty-flake-repro:
    - src/bake/ui/run/main.py: _process_is_exiting + _wait_no_reap (sysctl
      P_WEXIT poll, darwin-only) + rescue/finalize/wait inside guarded try
    - src/bake/ui/run/splitter.py: rescue_pending()
    - tests/unit/bake/ui/run/test_run.py: acceptance test + KI test patch
- NEXT (needs user): review diff, commit, push. Then CI repro x3 green,
  cleanup temp artifacts, decorator decision. NO merge to main without
  explicit user approval.

## Update (2026-10-02, decorator removal)

Removed @flaky_on_macos_ci from PTY-capture-path tests (fix covers them):

- tests/unit/bake/ui/run/test_run.py (13 decorators + import)
- tests/unit/bake/ui/run/test_script.py (2 + import)
- tests/unit/bake/cli/bakefile/test_run.py (1 + import)
  Kept (different flake mechanisms, not solved by this fix):
- tests/unit/bake/cli/bakefile/test_export.py:114 (shell parsing)
- tests/unit/bakelib/refreshable_cache/test_cache.py:120 (TTL timing)
  Edited files: 178 tests passed. Also: pty-flake-repro.yml now matrix x10
  parallel unit suite (user-requested), trace upload only on failure.

## Update (2026-10-02, decorators restored as comments)

User decision: restore @flaky_on_macos_ci as COMMENTS (not deleted) until
CI x10 proves the fix. All 17 back:

- tests/unit/bake/ui/run/test_run.py: 14 decorators + commented import
- tests/unit/bake/ui/run/test_script.py: 2 + import (regenerated from HEAD)
- tests/unit/bake/cli/bakefile/test_run.py: 1 + import (regenerated from HEAD)
  Kept active (unrelated mechanisms): test_export.py:114, cache TTL test.
  ruff I001 auto-fixed (blank line after commented import). 178 tests in
  edited files pass. Final full suite re-running.

Plan after CI x10 green: delete the 17 comment lines in follow-up commit,
re-run x10.

## Update (2026-10-02, CI x10 round 1 = 5/10 FAIL, root cause #2 found)

CI run 36945345579: 5/10 matrix jobs failed. Trace (pty-trace-x1) shows
stdout master fd first read returning b"" EOF 47ms into a RUNNING command.
Culprit: OutputSplitter._read_pty calls proc.poll() every loop iteration
(splitter.py:102). poll() = waitpid WNOHANG = wait syscall = destroys
unread master data (same kernel path as probe6). Reader threads destroy
the data themselves even with main-thread _wait_no_reap. Fix was
incomplete. Local tests missed it: starvation test data already rescued
by rescue_pending before reader poll could destroy.

Second suspect ruled out: main.py:870 poll() is kill-path only, safe.

Fix plan (user approved):

1. Probe A: confirm WNOHANG on RUNNING child destroys data (subagent)
2. Probe B: grandchild-holding-slave + reap order semantics (subagent)
3. Move _process_is_exiting to splitter.py (circular import), reader
   loop uses sysctl check on darwin, keeps poll() elsewhere
4. Main-thread order: rescue -> wait() -> finalize IF probe B supports
   (readers need master EOF after reap to exit; join before reap risks
   hang until drain_timeout)
5. Local: acceptance + suite + stress loop (verify spinner kill!)
6. Push, x10 again

## Update (2026-10-02, root cause #2 fixed: reader poll)

Probe A (20x each): WNOHANG harmless on running/pre-flip child (20/20
survive), but the wait call that first observes the child reapable
destroys unread data (0/20). Reader-loop proc.poll() is that call under
starvation.
Probe B (20x each): master EOF governed purely by slave-fd count. Leader
reap neither EOFs master nor destroys data while grandchild holds slave.
Join-before-reap cannot hang.

Changes:

- splitter.py: _process_is_exiting moved here + new _reader_should_drain
  (darwin = sysctl check, else poll). _read_pty guard uses it.
- main.py: local sysctl copy deleted, imports _process_is_exiting from
  splitter. Order unchanged: rescue -> finalize -> wait.
- test_run.py: new test_pty_reader_never_polls_the_child (monkeypatches
  Popen.poll to raise, darwin-only regression for root cause #2).
  Local: 149 test_run.py pass, ruff/format/ty clean. Full suite + 10x
  stress loop under 8 spinners (with verified cleanup) in flight.

## Update (2026-10-02, round-2 fix complete, awaiting push)

- test_splitter.py::test_read_pty_drains_on_process_exit updated: patches
  _process_is_exiting (darwin guard) alongside poll mock. 19 pass.
- Full suite clean machine: 2366 passed, 3 xfailed (89.98s).
- Stress: 10/10 both PTY regression tests under 8 spinners, spinner
  cleanup verified (0 left).
- READY: user commits + pushes, CI x10 round 2 decides decorator removal.

## Update (2026-10-02, CI round 2 = 2365/2366, test-only bug)

Run 36948258173: 10/10 jobs failed but ALL with the same single test
error, 2365 others passed. ZERO empty-capture failures = the actual
flake did not reproduce in 10 CI jobs. Fix itself holds.
Failure: patch("bake.ui.run.splitter._process_is_exiting") breaks on
py3.10: bake/ui/**init**.py does `from bake.ui.run import run` which
REBINDS bake.ui.run attr to the run() function; mock's dotted-name
_getter getattr-walk hits the function, AttributeError. Local 3.14
unaffected (mock resolution changed in newer CPython).
Fix: patch.object(import_module("bake.ui.run.splitter"),
"_process_is_exiting") -- module object, no dotted resolution.
test_splitter 19 pass, run/ dir 239 pass, lint clean. Ready for
commit + push, x10 round 3.

## Update (2026-10-02, CI round 3 = 5/10, mechanism B exposed)

Run 36949127007 (commit 49bc692): 5/10 fail (x3, x4, x6, x7, x9),
2364-2365 pass each. All failures = empty-capture signature, all in
tests/unit/bake/ui/run/. No collection/mock errors: py3.10 fix good.

Round 1 (5/10) trace showed destroy at 47ms by reader poll. Round 3
trace (x3, pid 3282) shows NO poll before read:

    264.069 RUN begin cmd=print('MARKER-STDOUT')
    264.716 read_pty start fd=13   <- reader first scheduled 647ms late
    264.717 read fd=13 len=0       <- data already gone

Failing runs all show elapsed_seconds 0.61-0.66s for `echo hello`
(x7: 0.610, x3: 0.658). That matches the ~0.65s no-wait decay timer
(context root cause #4): kernel discards unread master data ~0.65s
after child exit even with zero wait syscalls. CI runner starvation
(3 vCPU, xdist workers churning subprocesses) delays first read past
the timer. Coin flip -> 5/10.

Verdict: mechanism A (wait/poll-observing destroy) FIXED and proven.
Mechanism B (0.65s decay timer vs starved reads) remains. Under normal
load reads land well inside 0.65s; x10 stress on 3-vCPU runners sits
at the boundary.

Options discussed with user (2026-10-02), awaiting decision:

1. Probe: kill session leader. main.py:676 PTY path uses
   start_new_session=True; child = session leader. Suspect 0.65s
   discard = session-leader exit revoke. Probe child with setpgid
   (own pgrp, same session, no ctty): if master data survives past
   0.65s unreaped+unread, mechanism B dies = starvation-proof fix.
   Risk: signal/pgrp semantics (_kill_process_tree, SIGINT, SIGWINCH
   forwarding) need review.
2. Main-thread pump in _wait_no_reap (select+drain master fds each
   5ms loop). Weak: x3 trace shows whole-process stall (main thread
   stalled too, RUN end logged at 264.719).
3. Keep fix + decorators, cap CI xdist workers. Mitigation only.

## Update (2026-10-02, probe C: session-leader theory dead, slave-hold fix)

Probe C (/tmp/flake_loop/probeC.py, PROBEC_RESULT.txt), 20x each:

| Variant | Setup                                           | Lost  |
| ------- | ----------------------------------------------- | ----- |
| C1      | start_new_session (current), no wait, read 1.0s | 20/20 |
| C2      | setpgid only, same session, no wait, read 1.0s  | 20/20 |
| C3      | setpgid + reap 0.2s, read 1.0s                  | 20/20 |
| C4      | start_new_session + reap 0.2s, read 1.0s        | 20/20 |

Session leadership NOT the trigger. Bonus: ps shows child TTY=?? in all
variants -- subprocess start_new_session does setsid but never TIOCSCTTY,
so the child never had a controlling terminal anyway. The ~0.65s decay
fires on LAST SLAVE FD CLOSE, nothing else.

User picked option 1 (recommended): implement slave-hold fix, which was
already proven by probe3 A earlier (parent keeps one slave open, 0.8s
delay, lost 0/30).

Fix (main.py only):

- StreamSetup gains `slave_fds: tuple[int, ...] = ()`.
- _setup_pty_stream no longer closes slave_stdout/slave_stderr after
  spawn; stores them in StreamSetup.
- _run_with_split: local `slave_fds` list + idempotent _release_slave_fds
  closure. Order: _wait_no_reap -> rescue_pending -> RELEASE SLAVES ->
  finalize -> proc.wait(). Exception path: kill -> wait -> release ->
  finalize. finally releases too (OSError on wait/rescue cannot leak).
  Releasing before finalize gives readers in _drain_pty their EOF.

Verification (local): test_run + test_splitter 169 pass (incl.
test_pty_capture_survives_reader_starvation with reader delayed 1.0s >
0.65s decay = mechanism B acceptance); 20x run() capture + fd delta 0
(no leak); full suite 2366 passed / 3 xfailed (118s); ruff + format +
ty clean.

Status: AWAITING user commit + push, then CI x10 round 4. Decision
rule: 10/10 green -> remove the 17 commented decorators (follow-up
commit) + cleanup temp harness. Any empty-capture failure -> trace
decides; this was the last planned mechanism.

## Update (2026-10-02, round 4 = 10/10 GREEN, fix proven)

Run 36956751211 (commit 2603fe0, slave-hold fix): ALL 10 jobs success.
First fully green round. Round history: r1 5/10 (reader poll, fixed),
r2 2365/2366 (py3.10 mock bug, fixed), r3 5/10 (0.65s decay vs
starved reads, fixed by slave-hold), r4 10/10.

All three mechanisms now closed:

1. Wait-observing destroy -> sysctl P_WEXIT no-reap wait (a8af7b9)
2. Reader-thread poll destroy -> _reader_should_drain sysctl (acce2ca)
3. 0.65s last-slave-close decay -> parent holds slave fds until
   capture drained (2603fe0)

Remaining follow-ups (user decides):

- Remove 17 commented `# @flaky_on_macos_ci()` decorators + commented
  imports from test_run.py, test_script.py, cli/bakefile/test_run.py.
  Keep the 2 ACTIVE decorators (test_export.py shell parsing,
  test_cache.py TTL) -- unrelated mechanisms.
- Cleanup temp CI harness (delete): tests/utils/pty_trace.py,
  conftest.py PTY_TRACE gate, tests/unit/bake/ui/run/test_pty_flake_stress.py,
  .github/workflows/pty-flake-repro.yml, /tmp/flake_loop probe files.
- Keep regression tests: test_pty_capture_survives_reader_starvation,
  test_pty_reader_never_polls_the_child.
- NO merge to main without explicit user review.
