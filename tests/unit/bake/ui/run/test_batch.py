import importlib
import os
import subprocess
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
import typer

from bake import strip_ansi
from bake.ui.run.batch import (
    CliTask,
    CliTaskRunner,
    CompletedCliTask,
    ParallelCliTaskRunner,
    SequentialCliTaskRunner,
    spawn_env,
)

# Import the module (not the re-exported classes) so monkeypatch can patch its globals.
rc = importlib.import_module("bake.ui.run.batch")


def _make_fake_run(calls: list[dict]) -> Callable[..., subprocess.CompletedProcess[str]]:
    def _fake_run(
        cmd,
        *,
        cwd=None,
        dry_run=False,
        env=None,
        stream=False,
        capture_output=True,
        check=False,
        echo=False,
    ):
        calls.append(
            {
                "cmd": cmd,
                "cwd": cwd,
                "dry_run": dry_run,
                "env": env,
                "stream": stream,
                "capture_output": capture_output,
                "check": check,
                "echo": echo,
            }
        )
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="ok", stderr="")

    return _fake_run


class _SpyExecutor(ThreadPoolExecutor):
    _captured_max_workers: int | None = None

    def __init__(self, max_workers=None):
        type(self)._captured_max_workers = max_workers
        super().__init__(max_workers=max_workers)


def _result(
    returncode: int = 0, stdout: str = "", stderr: str = "", args=None
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=args if args is not None else ["c"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def _task(name: str = "c") -> CliTask:
    return CliTask(name=name, command=[name])


def _completed(
    name: str = "c",
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> CompletedCliTask:
    return CompletedCliTask(
        task=CliTask(name=name, command=[name]),
        result=_result(returncode=returncode, stdout=stdout, stderr=stderr),
    )


class TestParallelCliTaskRunner:
    def test_empty_tasks_leaves_completed_empty(self) -> None:
        runner = ParallelCliTaskRunner([])
        runner._run_tasks()
        assert runner.completed == []

    def test_completes_all_in_input_order(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[dict] = []
        monkeypatch.setattr(rc, "run", _make_fake_run(calls))
        tasks = [CliTask(name=f"t{i}", command=[f"cmd{i}"], cwd=f"cwd{i}") for i in range(3)]

        runner = ParallelCliTaskRunner(tasks)
        runner._run_tasks()

        # Appended completion-order, sorted back to input order for recap.
        assert [c.result.args for c in runner.completed] == [["cmd0"], ["cmd1"], ["cmd2"]]
        assert {c.task.cwd for c in runner.completed} == {"cwd0", "cwd1", "cwd2"}
        for item in runner.completed:
            assert item.result.returncode == 0

    def test_forwards_dry_run_and_task_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[dict] = []
        monkeypatch.setattr(rc, "run", _make_fake_run(calls))

        ParallelCliTaskRunner(
            [CliTask(name="t", command=["c"], cwd="d", env={"VIRTUAL_ENV": ""})],
            dry_run=True,
        )._run_tasks()

        assert calls[0]["dry_run"] is True
        assert calls[0]["env"] == {"VIRTUAL_ENV": ""}

    def test_task_without_env_forwards_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[dict] = []
        monkeypatch.setattr(rc, "run", _make_fake_run(calls))

        ParallelCliTaskRunner([CliTask(name="t", command=["c"], cwd="d")])._run_tasks()

        assert calls[0]["env"] is None

    def test_enforces_concurrency_safe_run_options(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[dict] = []
        monkeypatch.setattr(rc, "run", _make_fake_run(calls))

        ParallelCliTaskRunner([CliTask(name="t", command=["c"], cwd=None)])._run_tasks()

        assert calls[0]["stream"] is False
        assert calls[0]["capture_output"] is True
        assert calls[0]["check"] is False
        assert calls[0]["echo"] is True

    def test_task_echo_forwarded(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[dict] = []
        monkeypatch.setattr(rc, "run", _make_fake_run(calls))

        ParallelCliTaskRunner([CliTask(name="t", command=["c"], cwd=None, echo=True)])._run_tasks()

        assert calls[0]["echo"] is True

    def test_default_max_workers_clamped_to_task_count(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(rc, "run", _make_fake_run([]))
        monkeypatch.setattr(rc, "ThreadPoolExecutor", _SpyExecutor)
        tasks = [CliTask(name=f"t{i}", command=["c"], cwd=None) for i in range(2)]

        ParallelCliTaskRunner(tasks)._run_tasks()

        assert _SpyExecutor._captured_max_workers == 2

    def test_explicit_max_workers_clamped_to_task_count(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(rc, "run", _make_fake_run([]))
        monkeypatch.setattr(rc, "ThreadPoolExecutor", _SpyExecutor)
        tasks = [CliTask(name=f"t{i}", command=["c"], cwd=None) for i in range(3)]

        ParallelCliTaskRunner(tasks, max_workers=10)._run_tasks()

        assert _SpyExecutor._captured_max_workers == 3

    def test_run_all_success_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(rc, "run", _make_fake_run([]))
        tasks = [CliTask(name="a", command=["c"]), CliTask(name="b", command=["c"])]

        assert ParallelCliTaskRunner(tasks).run() is None

    def test_run_reusable_resets_state(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(rc, "run", _make_fake_run([]))
        tasks = [CliTask(name="a", command=["c"]), CliTask(name="b", command=["c"])]
        runner = ParallelCliTaskRunner(tasks, show_count=True)

        runner.run()
        first_completed = len(runner.completed)
        first_count = runner._completed_count

        runner.run()
        assert first_completed == 2
        assert first_count == 2
        assert len(runner.completed) == 2  # not 4
        assert runner._completed_count == 2  # not 4

    def test_run_failure_raises_exit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _failing_run(cmd, **_kwargs):
            return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="o", stderr="e")

        monkeypatch.setattr(rc, "run", _failing_run)

        with pytest.raises(typer.Exit) as exc:
            ParallelCliTaskRunner([CliTask(name="boom", command=["c"])]).run()

        assert exc.value.exit_code == 1


class TestSequentialCliTaskRunner:
    def test_empty_tasks_leaves_completed_empty(self) -> None:
        runner = SequentialCliTaskRunner([])
        runner._run_tasks()
        assert runner.completed == []

    def test_completes_all_in_input_order(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[dict] = []
        monkeypatch.setattr(rc, "run", _make_fake_run(calls))
        tasks = [CliTask(name=f"t{i}", command=[f"cmd{i}"], cwd=f"cwd{i}") for i in range(3)]

        runner = SequentialCliTaskRunner(tasks)
        runner._run_tasks()

        assert [c.task.name for c in runner.completed] == ["t0", "t1", "t2"]
        assert [c["cmd"] for c in calls] == [["cmd0"], ["cmd1"], ["cmd2"]]

    def test_forwards_dry_run_and_task_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[dict] = []
        monkeypatch.setattr(rc, "run", _make_fake_run(calls))

        SequentialCliTaskRunner(
            [CliTask(name="t", command=["c"], cwd="d", env={"VIRTUAL_ENV": ""})],
            dry_run=True,
        )._run_tasks()

        assert calls[0]["dry_run"] is True
        assert calls[0]["env"] == {"VIRTUAL_ENV": ""}

    def test_task_without_env_forwards_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[dict] = []
        monkeypatch.setattr(rc, "run", _make_fake_run(calls))

        SequentialCliTaskRunner([CliTask(name="t", command=["c"], cwd="d")])._run_tasks()

        assert calls[0]["env"] is None

    def test_enforces_stream_safe_run_options(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[dict] = []
        monkeypatch.setattr(rc, "run", _make_fake_run(calls))

        SequentialCliTaskRunner([CliTask(name="t", command=["c"], cwd=None)])._run_tasks()

        assert calls[0]["stream"] is True
        assert calls[0]["capture_output"] is False
        assert calls[0]["check"] is False
        assert calls[0]["echo"] is True

    def test_task_echo_forwarded(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[dict] = []
        monkeypatch.setattr(rc, "run", _make_fake_run(calls))

        runner = SequentialCliTaskRunner([CliTask(name="t", command=["c"], cwd=None, echo=True)])
        runner._run_tasks()

        assert calls[0]["echo"] is True

    def test_prints_status_per_task_after_streaming(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        monkeypatch.setattr(rc, "run", _make_fake_run([]))
        tasks = [CliTask(name="alpha", command=["c"]), CliTask(name="beta", command=["c"])]

        SequentialCliTaskRunner(tasks)._run_tasks()

        captured = capsys.readouterr()
        combined = strip_ansi(captured.out + captured.err)
        assert "alpha" in combined
        assert "beta" in combined

    def test_run_all_success_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(rc, "run", _make_fake_run([]))
        tasks = [CliTask(name="a", command=["c"]), CliTask(name="b", command=["c"])]

        assert SequentialCliTaskRunner(tasks).run() is None

    def test_run_reusable_keeps_count_in_range(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        monkeypatch.setattr(rc, "run", _make_fake_run([]))
        tasks = [_task("a"), _task("b")]
        runner = SequentialCliTaskRunner(tasks, show_count=True)

        runner.run()
        runner.run()

        combined = strip_ansi(capsys.readouterr().err)
        assert combined.count("[1/2]") == 2  # once per run
        assert combined.count("[2/2]") == 2
        assert "[3/2]" not in combined  # count did not leak across runs
        assert "[4/2]" not in combined

    def test_show_summary_false_skips_block_on_success(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        monkeypatch.setattr(rc, "run", _make_fake_run([]))
        runner = SequentialCliTaskRunner([_task("a"), _task("b")], show_summary=False)

        assert runner.run() is None

        combined = strip_ansi(capsys.readouterr().err)
        assert "Summary" not in combined

    def test_show_summary_false_still_raises_on_failure(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        def _failing_run(cmd, **_kwargs):
            return subprocess.CompletedProcess(args=cmd, returncode=1, stdout=None, stderr=None)

        monkeypatch.setattr(rc, "run", _failing_run)
        runner = SequentialCliTaskRunner([CliTask(name="boom", command=["c"])], show_summary=False)

        with pytest.raises(typer.Exit) as exc:
            runner.run()

        assert exc.value.exit_code == 1
        combined = strip_ansi(capsys.readouterr().err)
        assert "Summary" not in combined  # no block, but exit preserved

    def test_run_failure_raises_exit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _failing_run(cmd, **_kwargs):
            return subprocess.CompletedProcess(args=cmd, returncode=1, stdout=None, stderr=None)

        monkeypatch.setattr(rc, "run", _failing_run)

        with pytest.raises(typer.Exit) as exc:
            SequentialCliTaskRunner([CliTask(name="boom", command=["c"])]).run()

        assert exc.value.exit_code == 1


class TestReportTask:
    def test_success_prints_name(self, capsys: pytest.CaptureFixture) -> None:
        ParallelCliTaskRunner([])._report_task(_task("ok"), _result())

        captured = capsys.readouterr()
        assert "ok" in strip_ansi(captured.out + captured.err)

    def test_failure_dumps_output_and_status(self, capsys: pytest.CaptureFixture) -> None:
        ParallelCliTaskRunner([])._report_task(
            _task("boom"), _result(returncode=3, stdout="out blob", stderr="err blob")
        )

        captured = capsys.readouterr()
        combined = strip_ansi(captured.out + captured.err)
        assert "boom failed (exit 3)" in combined
        assert "stdout" in combined and "out blob" in combined
        assert "stderr" in combined and "err blob" in combined

    def test_show_fail_output_false_suppresses_dump(self, capsys: pytest.CaptureFixture) -> None:
        ParallelCliTaskRunner([], show_fail_output=False)._report_task(
            _task("boom"), _result(returncode=3, stdout="out blob", stderr="err blob")
        )

        captured = capsys.readouterr()
        combined = strip_ansi(captured.out + captured.err)
        assert "boom failed (exit 3)" in combined
        assert "out blob" not in combined
        assert "err blob" not in combined

    def test_success_output_hidden_by_default(self, capsys: pytest.CaptureFixture) -> None:
        ParallelCliTaskRunner([])._report_task(
            _task("ok"), _result(returncode=0, stdout="out blob", stderr="err blob")
        )

        captured = capsys.readouterr()
        combined = strip_ansi(captured.out + captured.err)
        assert "out blob" not in combined
        assert "err blob" not in combined

    def test_show_success_output_dumps_on_success(self, capsys: pytest.CaptureFixture) -> None:
        ParallelCliTaskRunner([], show_success_output=True)._report_task(
            _task("ok"), _result(returncode=0, stdout="out blob", stderr="err blob")
        )

        captured = capsys.readouterr()
        combined = strip_ansi(captured.out + captured.err)
        assert "out blob" in combined
        assert "err blob" in combined

    def test_show_count_in_status_within_dump_block(self, capsys: pytest.CaptureFixture) -> None:
        tasks = [_task("a"), _task("boom"), _task("c")]
        runner = ParallelCliTaskRunner(tasks, show_count=True)
        runner._report_task(tasks[1], _result(returncode=3, stdout="out blob"))

        combined = strip_ansi(capsys.readouterr().err)
        assert "[1/3] boom failed (exit 3)" in combined

    def test_begin_line_has_no_count(self, capsys: pytest.CaptureFixture) -> None:
        tasks = [_task("a"), _task("b")]
        runner = ParallelCliTaskRunner(tasks, show_count=True)
        runner.begin(tasks[1])

        combined = strip_ansi(capsys.readouterr().err)
        assert "Running b" in combined
        assert "[1/2]" not in combined and "[2/2]" not in combined

    def test_show_count_in_bare_status(self, capsys: pytest.CaptureFixture) -> None:
        tasks = [_task("a"), _task("boom"), _task("c")]
        runner = ParallelCliTaskRunner(tasks, show_count=True)
        runner._report_task(tasks[1], _result(returncode=3))  # no output → bare status

        combined = strip_ansi(capsys.readouterr().err)
        assert "[1/3] boom failed (exit 3)" in combined


class TestSummary:
    def test_all_success_prints_names_and_tally_no_raise(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        runner = CliTaskRunner([])
        runner.completed = [_completed(name="alpha"), _completed(name="beta")]
        runner.summary()

        captured = capsys.readouterr()
        combined = strip_ansi(captured.out + captured.err)
        assert "alpha" in combined
        assert "beta" in combined
        assert "2 passed" in combined
        assert "failed" not in combined

    def test_mixed_prints_tally_and_raises(self, capsys: pytest.CaptureFixture) -> None:
        runner = CliTaskRunner([])
        runner.completed = [_completed(name="ok"), _completed(name="boom", returncode=2)]

        with pytest.raises(typer.Exit) as exc:
            runner.summary()

        assert exc.value.exit_code == 1
        captured = capsys.readouterr()
        combined = strip_ansi(captured.out + captured.err)
        assert "1 passed" in combined
        assert "1 failed" in combined
        assert "boom failed (exit 2)" in combined

    def test_no_raise_when_all_success(self) -> None:
        runner = CliTaskRunner([])
        runner.completed = [_completed(name="ok")]
        runner.summary()  # no exception


class TestCliTaskRunnerBase:
    def test_base_run_tasks_raises_not_implemented(self) -> None:
        runner = CliTaskRunner([_task("a")])
        with pytest.raises(NotImplementedError):
            runner._run_tasks()

    def test_show_count_keeps_recap_status_clean(self, capsys: pytest.CaptureFixture) -> None:
        tasks = [_task("ok"), _task("boom")]
        runner = CliTaskRunner(tasks, show_count=True)
        runner.completed = [
            CompletedCliTask(task=tasks[0], result=_result()),
            CompletedCliTask(task=tasks[1], result=_result(returncode=2)),
        ]

        with pytest.raises(typer.Exit):
            runner.summary()

        combined = strip_ansi(capsys.readouterr().err)
        assert "ok failed" not in combined  # success → "ok", no count
        assert "boom failed (exit 2)" in combined  # recap status: no (N/M)
        assert "[1/2]" not in combined and "[2/2]" not in combined


class TestSpawnEnv:
    def test_no_args_clears_virtual_env_only(self) -> None:
        assert spawn_env() == {"VIRTUAL_ENV": ""}

    def test_clears_virtual_env_by_default(self) -> None:
        assert spawn_env("some/dir") == {"VIRTUAL_ENV": ""}

    def test_no_path_key_when_not_prepend(self) -> None:
        assert "PATH" not in spawn_env("proj")

    def test_prepend_venv_prepends_child_bin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PATH", "/usr/bin:/bin")
        env = spawn_env("proj", prepend_venv=True)

        venv_bin = os.path.join(os.path.abspath("proj"), ".venv", "bin")
        assert env["PATH"] == f"{venv_bin}:/usr/bin:/bin"

    def test_prepend_venv_with_none_cwd_uses_getcwd(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("PATH", "/usr/bin")
        monkeypatch.chdir(tmp_path)
        env = spawn_env(prepend_venv=True)

        assert env["PATH"].startswith(str(tmp_path / ".venv" / "bin"))

    def test_prepend_venv_resolves_relative_cwd_to_absolute(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PATH", "/usr/bin")
        env = spawn_env(tmp_path, prepend_venv=True)

        assert env["PATH"].startswith(str(tmp_path / ".venv" / "bin"))
        assert not str(tmp_path / ".venv" / "bin").startswith(".")
