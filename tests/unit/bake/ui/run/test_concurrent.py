import importlib
import os
import subprocess
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
import typer

from bake import strip_ansi
from bake.ui.run.concurrent import (
    CliTask,
    CompletedCliTask,
    report_completed_process,
    report_completed_processes,
    run_concurrently,
    run_concurrently_with_report,
    spawn_env,
)

# Grab the module object (not the same-named function re-exported into the
# package namespace) so monkeypatch can set its globals.
rc = importlib.import_module("bake.ui.run.concurrent")


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


class TestRunConcurrently:
    def test_empty_tasks_returns_empty_list(self) -> None:
        assert run_concurrently([]) == []

    def test_runs_all_tasks_in_input_order(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[dict] = []
        monkeypatch.setattr(rc, "run", _make_fake_run(calls))
        tasks = [CliTask(name=f"t{i}", command=[f"cmd{i}"], cwd=f"cwd{i}") for i in range(3)]

        completed = run_concurrently(tasks)

        assert len(completed) == 3
        # executor.map preserves input order; call log is completion-order
        assert [c.result.args for c in completed] == [["cmd0"], ["cmd1"], ["cmd2"]]
        assert {c.task.cwd for c in completed} == {"cwd0", "cwd1", "cwd2"}
        for item in completed:
            assert item.result.returncode == 0

    def test_forwards_dry_run_and_task_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[dict] = []
        monkeypatch.setattr(rc, "run", _make_fake_run(calls))

        run_concurrently(
            [CliTask(name="t", command=["c"], cwd="d", env={"VIRTUAL_ENV": ""})],
            dry_run=True,
        )

        assert calls[0]["dry_run"] is True
        assert calls[0]["env"] == {"VIRTUAL_ENV": ""}

    def test_task_without_env_forwards_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[dict] = []
        monkeypatch.setattr(rc, "run", _make_fake_run(calls))

        run_concurrently([CliTask(name="t", command=["c"], cwd="d")])

        assert calls[0]["env"] is None

    def test_enforces_concurrency_safe_run_options(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[dict] = []
        monkeypatch.setattr(rc, "run", _make_fake_run(calls))

        run_concurrently([CliTask(name="t", command=["c"], cwd=None)])

        assert calls[0]["stream"] is False
        assert calls[0]["capture_output"] is True
        assert calls[0]["check"] is False
        assert calls[0]["echo"] is False

    def test_task_echo_forwarded(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[dict] = []
        monkeypatch.setattr(rc, "run", _make_fake_run(calls))

        run_concurrently([CliTask(name="t", command=["c"], cwd=None, echo=True)])

        assert calls[0]["echo"] is True

    def test_default_max_workers_clamped_to_task_count(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[dict] = []
        monkeypatch.setattr(rc, "run", _make_fake_run(calls))
        monkeypatch.setattr(rc, "ThreadPoolExecutor", _SpyExecutor)
        tasks = [CliTask(name=f"t{i}", command=["c"], cwd=None) for i in range(2)]

        run_concurrently(tasks)

        assert _SpyExecutor._captured_max_workers == 2

    def test_explicit_max_workers_clamped_to_task_count(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[dict] = []
        monkeypatch.setattr(rc, "run", _make_fake_run(calls))
        monkeypatch.setattr(rc, "ThreadPoolExecutor", _SpyExecutor)
        tasks = [CliTask(name=f"t{i}", command=["c"], cwd=None) for i in range(3)]

        run_concurrently(tasks, max_workers=10)

        assert _SpyExecutor._captured_max_workers == 3


def _result(
    returncode: int = 0, stdout: str = "", stderr: str = "", args=None
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=args if args is not None else ["c"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


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


class TestReportCompletedProcess:
    def test_success_returns_false_and_prints_name(self, capsys: pytest.CaptureFixture) -> None:
        assert report_completed_process("ok", _result()) is False
        captured = capsys.readouterr()
        assert "ok" in captured.out + captured.err

    def test_failure_returns_true_and_dumps_output(self, capsys: pytest.CaptureFixture) -> None:
        failed = report_completed_process(
            "boom", _result(returncode=3, stdout="out blob", stderr="err blob")
        )

        assert failed is True
        captured = capsys.readouterr()
        combined = strip_ansi(captured.out + captured.err)
        assert "boom failed (exit 3)" in combined
        assert " stdout " in combined and "out blob" in combined
        assert " stderr " in combined and "err blob" in combined

    def test_show_fail_output_false_suppresses_dump(self, capsys: pytest.CaptureFixture) -> None:
        failed = report_completed_process(
            "boom",
            _result(returncode=3, stdout="out blob", stderr="err blob"),
            show_fail_output=False,
        )

        assert failed is True
        captured = capsys.readouterr()
        combined = strip_ansi(captured.out + captured.err)
        assert "boom failed (exit 3)" in combined
        assert "out blob" not in combined
        assert "err blob" not in combined
        assert " stdout " not in combined
        assert " stderr " not in combined

    def test_success_output_hidden_by_default(self, capsys: pytest.CaptureFixture) -> None:
        report_completed_process("ok", _result(returncode=0, stdout="out blob", stderr="err blob"))
        captured = capsys.readouterr()
        combined = strip_ansi(captured.out + captured.err)
        assert "out blob" not in combined
        assert "err blob" not in combined

    def test_show_success_output_dumps_on_success(self, capsys: pytest.CaptureFixture) -> None:
        report_completed_process(
            "ok",
            _result(returncode=0, stdout="out blob", stderr="err blob"),
            show_success_output=True,
        )
        captured = capsys.readouterr()
        combined = strip_ansi(captured.out + captured.err)
        assert "out blob" in combined
        assert "err blob" in combined


class TestReportCompletedProcesses:
    def test_all_success_prints_names(self, capsys: pytest.CaptureFixture) -> None:
        completed = [_completed(name="alpha"), _completed(name="beta")]

        report_completed_processes(completed)

        captured = capsys.readouterr()
        combined = strip_ansi(captured.out + captured.err)
        assert "alpha" in combined
        assert "beta" in combined
        assert "failed" not in combined

    def test_mixed_dumps_output_and_raises(self, capsys: pytest.CaptureFixture) -> None:
        completed = [
            _completed(name="ok"),
            _completed(name="boom", returncode=2, stdout="out blob", stderr="err blob"),
        ]

        with pytest.raises(typer.Exit) as exc:
            report_completed_processes(completed)

        assert exc.value.exit_code == 1
        captured = capsys.readouterr()
        combined = strip_ansi(captured.out + captured.err)
        assert "boom failed (exit 2)" in combined
        assert " stdout " in combined and "out blob" in combined
        assert " stderr " in combined and "err blob" in combined

    def test_show_fail_output_false_suppresses_dump_but_raises(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        completed = [
            _completed(name="ok"),
            _completed(name="boom", returncode=2, stdout="out blob", stderr="err blob"),
        ]

        with pytest.raises(typer.Exit) as exc:
            report_completed_processes(completed, show_fail_output=False)

        assert exc.value.exit_code == 1
        captured = capsys.readouterr()
        combined = strip_ansi(captured.out + captured.err)
        assert "boom failed (exit 2)" in combined
        assert "out blob" not in combined
        assert "err blob" not in combined

    def test_raises_on_failure(self) -> None:
        completed = [_completed(name="boom", returncode=1)]

        with pytest.raises(typer.Exit) as exc:
            report_completed_processes(completed)

        assert exc.value.exit_code == 1

    def test_no_raise_when_all_success(self) -> None:
        completed = [_completed(name="ok")]

        assert report_completed_processes(completed) is None


class TestRunConcurrentlyWithReport:
    def test_all_success_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(rc, "run", _make_fake_run([]))
        tasks = [CliTask(name="a", command=["c"]), CliTask(name="b", command=["c"])]

        assert run_concurrently_with_report(tasks) is None

    def test_failure_raises_exit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _failing_run(cmd, **_kwargs):
            return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="o", stderr="e")

        monkeypatch.setattr(rc, "run", _failing_run)

        with pytest.raises(typer.Exit) as exc:
            run_concurrently_with_report([CliTask(name="boom", command=["c"])])

        assert exc.value.exit_code == 1


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
