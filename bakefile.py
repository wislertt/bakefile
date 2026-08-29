import logging
import os
import re
import signal
import subprocess
import sys
from pathlib import Path
from textwrap import dedent
from typing import Annotated

import typer
import zerv

from bake import (
    DEFAULT_BAKE_LOG,
    DEFAULT_BAKE_LOG_PRETTY,
    CliTask,
    ParallelCliTaskRunner,
    command,
    console,
    spawn_env,
    strip_ansi,
)
from bake.ui import run
from bakelib import GitHubActionsTools, PythonLibSpace, params
from scripts.locked_pins import (
    PYPROJECT_PATH,
    UV_LOCK_PATH,
    guard_invariants,
    locked_pin_specs,
    parse_lock_versions,
    relax_locked_pins,
    rewrite_locked_pins,
)

logger = logging.getLogger(__name__)


class MyBakebook(GitHubActionsTools, PythonLibSpace):
    bake_log: str = DEFAULT_BAKE_LOG
    bake_log_verbosity: params.BakeLogVerbosityField = 3
    bake_log_pretty: bool = DEFAULT_BAKE_LOG_PRETTY

    def test(self, durations: params.DurationsOption = None) -> None:
        self._test(tests_paths="tests/unit/", parallel=True, durations=durations)

    def _get_mise_tools(self) -> set[str]:
        mise_tools = super()._get_mise_tools()
        mise_tools.remove("pipx:bakefile[extras=locked]")
        mise_tools.add("npm:mintlify")
        return mise_tools

    def _update_project(self) -> None:
        super()._update_project()
        self._update_locked_pins()
        self._update_examples()
        self._update_hooks()

    def _update_locked_pins(self) -> None:
        original_text = PYPROJECT_PATH.read_text()
        relaxed_text, relaxed = relax_locked_pins(original_text)
        if relaxed:
            console.info(f"Relaxed {len(relaxed)} [locked] pins to base floors")
        if relaxed and not self.ctx.dry_run:
            PYPROJECT_PATH.write_text(relaxed_text)

        self.ctx.run("uv lock --upgrade")

        lock_map = parse_lock_versions(UV_LOCK_PATH.read_text())
        new_text, _changes = rewrite_locked_pins(lock_map, PYPROJECT_PATH.read_text())
        before = locked_pin_specs(original_text)
        after = locked_pin_specs(new_text)
        for name in sorted(after):
            if before.get(name) != after[name]:
                console.info(f"[locked] {name}: {before.get(name)} -> {after[name]}")
        if new_text == PYPROJECT_PATH.read_text():
            return
        if self.ctx.dry_run:
            console.info(f"Would update {PYPROJECT_PATH} (dry run)")
            return
        PYPROJECT_PATH.write_text(new_text)
        console.success(f"Updated {PYPROJECT_PATH}")

    def lint(self) -> None:
        super().lint()
        self._guard_locked_pins()

    def _guard_locked_pins(self) -> None:
        lock_map = parse_lock_versions(UV_LOCK_PATH.read_text())
        violations = guard_invariants(lock_map, PYPROJECT_PATH.read_text())
        if not violations:
            console.success("[locked] pins consistent with base floors and uv.lock")
            return
        for violation in violations:
            console.error(violation)
        raise typer.Exit(1)

    def _example_tasks(self, bake_command: str) -> list[CliTask]:
        examples_dir = Path("examples")
        if not examples_dir.exists():
            return []
        return [
            CliTask(
                name=example_dir.name,
                command=["bake", *bake_command.split()],
                cwd=example_dir,
                env=spawn_env(example_dir, prepend_venv=True),
                echo=True,
            )
            for example_dir in sorted(examples_dir.iterdir())
            if example_dir.is_dir()
        ]

    def _update_examples(self) -> None:
        ParallelCliTaskRunner(
            self._example_tasks("update -ff"),
            dry_run=self.ctx.dry_run,
            show_count=True,
            show_summary=False,
        ).run()

    def _update_hooks(self) -> None:
        hooks_dir = Path(".claude/hooks")
        console.start(f"Updating {hooks_dir}")
        self.ctx.run("bun update", cwd=hooks_dir)

    @command()
    def uvx_install_bake_local(
        self,
        editable: Annotated[
            bool, typer.Option("--editable", "-e", help="Install in editable mode")
        ] = False,
    ):
        new_version = zerv.flow(schema="standard-base-prerelease-post-dev", output_format="pep440")
        with self._version_bump_context(new_version):
            editable_flag = "-e " if editable else ""
            self.ctx.run(f"uv tool install {editable_flag}.[lib] --reinstall --force")

    @command()
    def docs(self):
        self.ctx.run("mintlify dev", cwd=Path("docs"))

    @command()
    def docs_check(self):
        self.ctx.run("mintlify broken-links", cwd=Path("docs"))


bakebook = MyBakebook()


@bakebook.command()
def uvx_install_bake():
    bakebook.ctx.run("uv tool install 'bakefile[lib]' --reinstall")


@bakebook.command()
def uvx_install_bake_test():
    bakebook.ctx.run(
        dedent("""\
        uv tool install 'bakefile[lib]' \\
            --index-url https://test.pypi.org/simple/ \\
            --extra-index-url https://pypi.org/simple \\
            --prerelease allow \\
            --reinstall \\
            --index-strategy unsafe-best-match
    """)
    )


# demo: "polite" child (isatty-gated progress bar, like pip/uv/npm) under all three run() modes
_DEMO_CHILD = r"""
import fcntl, shutil, struct, sys, termios, time

def winsize():
    try:
        ws = fcntl.ioctl(1, termios.TIOCGWINSZ, b"\x00" * 8)
        rows, cols, _, _ = struct.unpack("HHHH", ws)
        return f"{cols}x{rows}"
    except OSError:
        return "ioctl-failed"

fallback = shutil.get_terminal_size()
print(f"[child] isatty={sys.stdout.isatty()} ioctl_winsize={winsize()}"
      f" fallback={fallback.columns}x{fallback.lines}")

if sys.stdout.isatty():
    for i in range(10):
        bar = '#' * ((i + 1) * 2)
        sys.stdout.write('\r\x1b[K[%-20s] \x1b[31m%d%%\x1b[0m' % (bar, (i + 1) * 10))
        sys.stdout.flush()
        time.sleep(0.05)
    sys.stdout.write('\n')
else:
    for i in range(10):
        print(f'progress {(i + 1) * 10}%')
print('DONE')
"""


def _demo_section(title: str) -> None:
    console.echo("")
    console.echo(f"===== {title} =====", markup=False)


def _demo_status(fixed: bool, note: str) -> None:
    if fixed:
        console.success(f"FIXED: {note}")
    else:
        console.error(f"STILL BROKEN: {note}")


# demo: multi-line redraw (npm/cargo style) overdraws its width by 30 cols -> cursor-up miscounts
_STREAM_BREAK_CHILD = r"""
import os, sys, time

width = int(os.environ.get("COLUMNS", 80)) + 30  # overdraw: wider than real terminal
print(f"[child] drawing {width} cols wide, 3-row frames, cursor-up 3")
sys.stdout.flush()
for i in range(15):
    pct = (i + 1) * 100 // 15
    bar = "#" * (pct * (width - 12) // 100)
    frame = [
        ("[" + bar).ljust(width - 8) + "] " + str(pct) + "%",
        ("speed " + str(5 + i) + " MB/s").ljust(width),
        ("resolved " + str(i + 1) + "/15 packages").ljust(width),
    ]
    if i > 0:
        sys.stdout.write("\x1b[3A")  # cursor up 3 rows (wrong once rows wrap)
    sys.stdout.write("\n".join(frame) + "\n")
    sys.stdout.flush()
    time.sleep(0.08)
sys.stdout.write("DONE\n")
"""


# honest tool: sizes frames from real ioctl winsize, 80 fallback only when unavailable
_HONEST_WIDTH_CHILD = r"""
import fcntl, struct, sys, termios, time

try:
    ws = fcntl.ioctl(1, termios.TIOCGWINSZ, b"\x00" * 8)
    raw_ws_col = struct.unpack("HHHH", ws)[1]
    print(f"[child] raw ws_col: {raw_ws_col}")
    width = raw_ws_col or 80
except OSError:
    raw_ws_col = -1
    width = 80
print(f"[child] ioctl width: {width}")
sys.stdout.flush()
for i in range(15):
    pct = (i + 1) * 100 // 15
    bar = "#" * (pct * (width - 12) // 100)
    frame = [
        ("[" + bar).ljust(width - 8) + "] " + str(pct) + "%",
        ("speed " + str(5 + i) + " MB/s").ljust(width),
        ("resolved " + str(i + 1) + "/15 packages").ljust(width),
    ]
    if i > 0:
        sys.stdout.write("\x1b[3A")
    sys.stdout.write("\n".join(frame) + "\n")
    sys.stdout.flush()
    time.sleep(0.08)
sys.stdout.write("DONE\n")
"""


@bakebook.command()
def demo1():
    _demo_section("1. stream + capture, honest child (PTY, ioctl-sized frames)")
    result = run([sys.executable, "-c", _HONEST_WIDTH_CHILD], capture_output=True, echo=False)
    console.echo(f"captured splitlines: {len(result.stdout.splitlines())}", markup=False)
    console.echo("note: capture keeps every redraw frame - cleaned up in task 6", markup=False)

    _demo_section("2. stream only, honest child (pipe, not a tty -> 80 fallback)")
    run([sys.executable, "-c", _HONEST_WIDTH_CHILD], capture_output=False, echo=False)

    _demo_section("3. honest child via PTY: bake passes real winsize")
    probed = run([sys.executable, "-c", _HONEST_WIDTH_CHILD], capture_output=True, echo=False)
    match = re.search(r"raw ws_col: (-?\d+)", probed.stdout)
    raw_ws_col = int(match.group(1)) if match else 0
    _demo_status(raw_ws_col > 0, f"honest child sees nonzero PTY winsize (raw ws_col={raw_ws_col})")

    _demo_section("4. contrast: over-drawing child garbles with NO bake (child bug)")
    console.echo(f"[parent] COLUMNS env: {os.environ.get('COLUMNS')!r}", markup=False)
    subprocess.run([sys.executable, "-c", _STREAM_BREAK_CHILD], check=True)


@bakebook.command()
def demo2():
    _demo_section("1. stream + capture (PTY tee)")
    result = run([sys.executable, "-c", _DEMO_CHILD], capture_output=True, echo=False)
    console.echo(f"captured: {strip_ansi(result.stdout)!r}", markup=False)
    match = re.search(r"ioctl_winsize=(\S+)", result.stdout)
    ws = match.group(1) if match else "?"
    _demo_status(
        ws not in ("0x0", "ioctl-failed", "?"),
        f"PTY carries real winsize to child (ioctl_winsize={ws})",
    )

    _demo_section("2. stream only (inherit real tty)")
    result = run([sys.executable, "-c", _DEMO_CHILD], capture_output=False, echo=False)
    console.echo(f"captured: {result.stdout!r}")

    _demo_section("3. capture only (pipe)")
    result = run(
        [sys.executable, "-c", _DEMO_CHILD],
        capture_output=True,
        stream=False,
        echo=False,
    )
    console.echo(f"captured: {strip_ansi(result.stdout)!r}", markup=False)


# demo3: grandchild writes AFTER child exit; bake drains to EOF, capped by drain_timeout
_GRANDCHILD_TAIL_CHILD = r"""
import subprocess, sys

subprocess.Popen(
    [sys.executable, "-c", "import time; time.sleep(1.5); print('LATE OUTPUT FROM GRANDCHILD')"],
)
print("main child done, grandchild prints 1.5s later")
"""


@bakebook.command()
def demo3():
    _demo_section("bake: grandchild output after main proc exit is captured")
    result = run([sys.executable, "-c", _GRANDCHILD_TAIL_CHILD], capture_output=True, echo=False)
    console.echo(f"captured: {result.stdout!r}", markup=False)
    console.echo(f"LATE OUTPUT present in capture: {'LATE OUTPUT' in result.stdout}")

    _demo_section("plain subprocess waits for pipe EOF, captures it")
    plain = subprocess.run(
        [sys.executable, "-c", _GRANDCHILD_TAIL_CHILD], capture_output=True, check=False
    )
    console.echo(f"plain captured: {plain.stdout!r}", markup=False)
    console.echo(f"LATE OUTPUT present in capture: {'LATE OUTPUT' in plain.stdout.decode()}")


# demo4: default decode replaces invalid UTF-8 with U+FFFD; surrogateescape keeps raw bytes
_DECODE_CHILD = r"""
import sys

sys.stdout.buffer.write(b"ok line\n\xff\xfe invalid utf8 bytes\n")
sys.stdout.buffer.flush()
"""


@bakebook.command()
def demo4():
    _demo_section("invalid UTF-8 silently replaced in capture")
    result = run([sys.executable, "-c", _DECODE_CHILD], capture_output=True, echo=False)
    console.echo(f"captured repr: {result.stdout!r}", markup=False)
    plain = subprocess.run([sys.executable, "-c", _DECODE_CHILD], capture_output=True, check=True)
    opt_in = run(
        [sys.executable, "-c", _DECODE_CHILD],
        capture_output=True,
        echo=False,
        decode_errors="surrogateescape",
    )
    roundtrip = opt_in.stdout.encode("utf-8", "surrogateescape")
    console.echo(
        f"surrogateescape round-trip == raw bytes: {roundtrip == plain.stdout}", markup=False
    )
    console.echo(f"plain subprocess repr: {plain.stdout!r}", markup=False)


_FAST_OUTPUT_CHILD = r"""
import sys

chunk = "x" * 4096 + "\n"
for _ in range(4096):  # ~16MB
    sys.stdout.write(chunk)
"""

_BENCH_BYTES = 4096 * 4097


@bakebook.command()
def demo5():
    import contextlib
    import statistics
    import tempfile
    import time as time_mod

    _demo_section("throughput: 16MB fast output, PTY tee vs plain pipe (median of 3)")

    def median_secs(fn) -> float:
        samples = []
        for _ in range(3):
            with tempfile.TemporaryFile("w") as sink, contextlib.redirect_stdout(sink):
                start = time_mod.perf_counter()
                fn()
            samples.append(time_mod.perf_counter() - start)
        return statistics.median(samples)

    def bake_run() -> int:
        result = run([sys.executable, "-c", _FAST_OUTPUT_CHILD], capture_output=True, echo=False)
        return len(result.stdout)

    def plain_run() -> int:
        plain = subprocess.run(
            [sys.executable, "-c", _FAST_OUTPUT_CHILD], capture_output=True, check=True
        )
        return len(plain.stdout)

    bake_secs = median_secs(bake_run)
    plain_secs = median_secs(plain_run)
    mb_per_sec = _BENCH_BYTES / 1e6
    console.echo(f"bake PTY stream+capture: {bake_secs:.2f}s ({mb_per_sec / bake_secs:.0f} MB/s)")
    console.echo(f"plain pipe subprocess:   {plain_secs:.2f}s ({mb_per_sec / plain_secs:.0f} MB/s)")
    console.echo(f"ratio PTY/pipe: {bake_secs / plain_secs:.2f}x (target <= 1.5x)")


# demo6: bake forces FORCE_COLOR + PTY, so children emit ANSI even when bake's stdout is a pipe
_COLORED_CHILD = r"""
import sys

if sys.stdout.isatty() or __import__("os").environ.get("FORCE_COLOR"):
    sys.stdout.write("\x1b[31mRED LINE\x1b[0m\n")
else:
    sys.stdout.write("RED LINE (plain)\n")
"""


@bakebook.command()
def demo6():
    _demo_section("ANSI forced through even when bake output is piped (CI)")
    result = run([sys.executable, "-c", _COLORED_CHILD], capture_output=True, echo=False)
    console.echo(f"captured repr: {result.stdout!r}", markup=False)
    console.echo(f"bake stdout isatty: {sys.stdout.isatty()}")
    plain = subprocess.run([sys.executable, "-c", _COLORED_CHILD], capture_output=True, check=True)
    console.echo(f"plain subprocess repr: {plain.stdout!r}", markup=False)


@bakebook.command()
def demo7():
    _demo_section("omitted capture_output: runtime stdout must be None and ty must reject str use")
    result = run(["echo", "hi"], echo=False)
    console.echo(f"runtime stdout: {result.stdout!r}")

    _demo_section("probe with ty: omitted arg passes bad annotation, explicit fails")
    probe_rejections: list[bool] = []
    probes = {
        "A_omitted": (
            "from bake.ui import run\nr = run(['echo', 'hi'])\nneeds_str: str = r.stdout\n"
        ),
        "B_explicit_false": (
            "from bake.ui import run\n"
            "r = run(['echo', 'hi'], capture_output=False)\n"
            "needs_str: str = r.stdout\n"
        ),
    }
    for name, src in probes.items():
        probe_path = Path(f"/tmp/_probe7_{name}.py")
        probe_path.write_text(src)
        res = subprocess.run(
            [sys.executable, "-m", "ty", "check", str(probe_path)],
            capture_output=True,
            text=True,
        )
        verdict = "accepted (type lie)" if res.returncode == 0 else "rejected (honest)"
        console.echo(f"probe {name}: {verdict}", markup=False)
        probe_rejections.append(res.returncode != 0)

    _demo_status(
        result.stdout is None and all(probe_rejections),
        "omitted capture_output gives stdout None and ty rejects str use",
    )


_SLOW_CHILD = r"""
import sys, time

print("START")
sys.stdout.flush()
time.sleep(5)
print("END")
"""


@bakebook.command()
def demo8():
    _demo_section("bake: TimeoutExpired discards partial output")
    try:
        run([sys.executable, "-c", _SLOW_CHILD], capture_output=True, timeout=1, echo=False)
    except subprocess.TimeoutExpired as exc:
        console.echo(f"exc.stdout: {exc.stdout!r}", markup=False)

    _demo_section("plain subprocess: TimeoutExpired carries partial output")
    try:
        subprocess.run(
            [sys.executable, "-c", _SLOW_CHILD], capture_output=True, timeout=1, check=False
        )
    except subprocess.TimeoutExpired as exc:
        console.echo(f"exc.stdout: {exc.stdout!r}", markup=False)


_OUTER_RUNNER = r"""
import sys

from bake.ui import run

try:
    run(["/bin/sleep", "30"], capture_output=True, echo=False)
except KeyboardInterrupt:
    sys.exit(130)
"""


@bakebook.command()
def demo9():
    import time

    def _sleep_alive() -> bool:
        found = subprocess.run(["pgrep", "-f", "/bin/sleep 30"], capture_output=True, text=True)
        return bool(found.stdout.strip())

    def _kill_sleeps() -> None:
        subprocess.run(["pkill", "-f", "/bin/sleep 30"], check=False)
        time.sleep(0.2)

    _kill_sleeps()
    _demo_section("SIGTERM to bake: children orphaned")
    outer = subprocess.Popen([sys.executable, "-c", _OUTER_RUNNER])
    time.sleep(1.5)
    os.kill(outer.pid, signal.SIGTERM)
    console.echo(f"outer returncode: {outer.wait()}")
    time.sleep(0.5)
    console.echo(f"sleep still running after SIGTERM: {_sleep_alive()}")

    _kill_sleeps()
    _demo_section("SIGINT to bake: _sigint_guard kills the tree")
    outer = subprocess.Popen([sys.executable, "-c", _OUTER_RUNNER])
    time.sleep(1.5)
    os.kill(outer.pid, signal.SIGINT)
    console.echo(f"outer returncode: {outer.wait()}")
    time.sleep(0.5)
    console.echo(f"sleep still running after SIGINT: {_sleep_alive()}")
    _kill_sleeps()


def _fd_count() -> int:
    return len(os.listdir("/dev/fd"))


@bakebook.command()
def demo10():
    import contextlib

    _demo_section("bake: failed spawn must not leak PTY fds")
    before = _fd_count()
    for _ in range(3):
        with contextlib.suppress(FileNotFoundError):
            run(["bake-nonexistent-cmd-xyz"], capture_output=True, echo=False)
    after = _fd_count()
    fail_delta = after - before
    console.echo(f"fds: {before} -> {after} (delta {fail_delta})")
    _demo_status(fail_delta == 0, f"failed spawns leak no fds (delta {fail_delta})")

    _demo_section("successful runs close everything")
    before = _fd_count()
    for _ in range(3):
        run(["echo", "ok"], capture_output=True, echo=False)
    after = _fd_count()
    ok_delta = after - before
    console.echo(f"fds: {before} -> {after} (delta {ok_delta})")
    _demo_status(ok_delta == 0, f"successful runs leak no fds (delta {ok_delta})")


_RICH_COLOR_CHILD = r"""
import os, sys

# mirrors rich-family color detection: FORCE_COLOR beats NO_COLOR
if os.environ.get("FORCE_COLOR"):
    sys.stdout.write("\x1b[31mCOLORED\x1b[0m\n")
else:
    sys.stdout.write("PLAIN\n")
"""


@bakebook.command()
def demo11():
    _demo_section("user sets NO_COLOR=1: bake must not inject FORCE_COLOR")
    result = run(
        [sys.executable, "-c", _RICH_COLOR_CHILD],
        capture_output=True,
        env={"NO_COLOR": "1"},
        echo=False,
    )
    console.echo(f"captured: {result.stdout!r}", markup=False)
    _demo_status(
        "\x1b" not in result.stdout,
        "NO_COLOR beats injected FORCE_COLOR (child prints PLAIN)",
    )

    _demo_section("plain subprocess honors NO_COLOR")
    plain_env = dict(os.environ, NO_COLOR="1")
    plain_env.pop("FORCE_COLOR", None)
    plain = subprocess.run(
        [sys.executable, "-c", _RICH_COLOR_CHILD],
        capture_output=True,
        env=plain_env,
        check=False,
    )
    console.echo(f"captured: {plain.stdout!r}", markup=False)


# demo12: PTY-path resize; bake refreshes master winsize + killpg SIGWINCH (no ctty - see demo3)
_RESIZE_CHILD = r"""
import fcntl, signal, struct, sys, termios, time

def width():
    try:
        return struct.unpack("HHHH", fcntl.ioctl(1, termios.TIOCGWINSZ, b"\x00" * 8))[1] or 80
    except OSError:
        return 0

winch = 0

def on_winch(signum, frame):
    global winch
    winch += 1

signal.signal(signal.SIGWINCH, on_winch)

for _ in range(40):  # ~4s, one width report per 0.1s - resize and watch
    print(f"{width()}c", flush=True)
    time.sleep(0.1)
print(f"[child] SIGWINCH signals: {winch}", flush=True)
"""


@bakebook.command()
def demo12():
    _demo_section("1. bake: RESIZE TERMINAL NOW (~4s)")
    result = run([sys.executable, "-c", _RESIZE_CHILD], capture_output=True, echo=False)
    match = re.search(r"SIGWINCH signals: (\d+)", result.stdout)
    winch_count = int(match.group(1)) if match else 0
    console.echo(f"child SIGWINCH signals under bake: {winch_count}")
    console.echo("(width lines above should have tracked your resize)")
    _demo_status(
        winch_count > 0,
        "child receives SIGWINCH under bake (resize forwarded via killpg)",
    )

    _demo_section("2. plain subprocess: RESIZE TERMINAL NOW (~4s)")
    console.echo("width lines track resize AND signal count goes up on each resize")
    subprocess.run([sys.executable, "-c", _RESIZE_CHILD], check=False)


# demo13: stream-only pipe path; frozen COLUMNS + start_new_session block live resize
_PIPE_RESIZE_CHILD = r"""
import fcntl, os, signal, struct, sys, termios, time

def width():
    try:
        return struct.unpack("HHHH", fcntl.ioctl(1, termios.TIOCGWINSZ, b"\x00" * 8))[1] or 80
    except OSError:
        return 0

winch = 0

def on_winch(signum, frame):
    global winch
    winch += 1

signal.signal(signal.SIGWINCH, on_winch)

for _ in range(40):  # ~4s, one report per 0.1s - resize and watch
    print(f"ioctl={width()}c env={os.environ.get('COLUMNS', '<unset>')} winch={winch}", flush=True)
    time.sleep(0.1)
sys.exit(0 if winch else 1)
"""


@bakebook.command()
def demo13():
    _demo_section("1. bake stream-only (the bake test path): RESIZE TERMINAL NOW (~4s)")
    console.echo("watch: ioctl= follows the resize, env= stays frozen, winch stays 0")
    result = run(
        [sys.executable, "-c", _PIPE_RESIZE_CHILD],
        stream=True,
        capture_output=False,
        check=False,
        echo=False,
    )
    _demo_status(
        result.returncode == 0,
        "stream-only child receives SIGWINCH (pipe path forwards resizes)",
    )

    _demo_section("2. plain subprocess: RESIZE TERMINAL NOW (~4s)")
    console.echo("ioctl= follows, env=<unset>, winch climbs on every resize")
    completed = subprocess.run([sys.executable, "-c", _PIPE_RESIZE_CHILD], check=False)
    _demo_status(
        completed.returncode == 0,
        "plain subprocess child receives SIGWINCH (foreground process group)",
    )
