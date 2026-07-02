import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import typer

from bake.ui import console
from bake.ui.run.main import CmdType, _dump_output, _separator, run


@dataclass(frozen=True, slots=True)
class CliTask:
    name: str
    command: CmdType
    cwd: Path | str | None = None
    env: dict[str, str] | None = None


@dataclass(frozen=True, slots=True)
class CompletedCliTask:
    task: CliTask
    result: subprocess.CompletedProcess[str]


def _run_cli_task(
    task: CliTask,
    *,
    dry_run: bool,
    env: dict[str, str] | None,
) -> subprocess.CompletedProcess[str]:
    # Concurrency-safe options: stream=False (no cross-thread interleave),
    # capture_output=True, check=False (one failure must not abort siblings),
    # echo=False. Task-level env wins over the caller-supplied default.
    return run(
        task.command,
        cwd=task.cwd,
        dry_run=dry_run,
        env=task.env if task.env is not None else env,
        stream=False,
        capture_output=True,
        check=False,
        echo=False,
    )


def run_concurrently(
    tasks: list[CliTask],
    *,
    max_workers: int | None = None,
    dry_run: bool = False,
    env: dict[str, str] | None = None,
) -> list[CompletedCliTask]:
    """Run :class:`CliTask` instances concurrently via a thread pool.

    Thin concurrency wrapper over :func:`run`. ``run`` guards
    ``subprocess.Popen`` with a process-wide lock, so concurrent calls are
    safe.

    Each task runs with ``stream=False, capture_output=True, check=False,
    echo=False``: streaming would interleave output across threads, and
    ``check=False`` keeps one failed task from aborting its siblings. The
    caller owns exit-code policy (e.g. raising ``typer.Exit`` after
    inspecting ``returncode``).

    Parameters
    ----------
    tasks
        Tasks to run. Order is preserved in the returned list.
    max_workers
        Thread cap. Defaults to ``min(len(tasks), os.cpu_count() or 4)``;
        an explicit value is clamped to ``len(tasks)``.
    dry_run
        Forwarded to :func:`run`; tasks print without executing.
    env
        Environment overrides forwarded to :func:`run` for tasks that
        do not carry their own ``env``. A task-level ``CliTask.env`` wins.

    Returns
    -------
    list[CompletedCliTask]
        One :class:`CompletedCliTask` per input task, in input order.

    Notes
    -----
    SIGINT does not reliably kill in-flight children: ``run``'s
    signal guard is a no-op off the main thread, and process handles live
    inside worker threads where they cannot be reached from the caller.
    """
    if not tasks:
        return []

    workers = min(max_workers or (os.cpu_count() or 4), len(tasks))

    def _run_task(task: CliTask) -> CompletedCliTask:
        console.start(f"Running {task.name}")
        return CompletedCliTask(task=task, result=_run_cli_task(task, dry_run=dry_run, env=env))

    with ThreadPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(_run_task, tasks))


def report_completed_process(
    name: str, result: subprocess.CompletedProcess[str], *, summary: bool = False
) -> bool:
    """Report one process's outcome.

    Prints ``console.success(name)`` on success, or ``console.error(...)``
    plus captured stdout/stderr on failure.

    Returns ``True`` if the process failed.

    Parameters
    ----------
    summary
        When ``True``, print only the success/error line and suppress the
        captured stdout/stderr dump (e.g. for a compact summary view).
    """
    if result.returncode == 0:
        console.success(name)
        return False
    console.error(f"{name} failed (exit {result.returncode})")
    # Separator closes the dump block; skip when summarizing or nothing to dump.
    if not summary and (result.stdout or result.stderr):
        _dump_output(result, name)
        _separator()
        console.err.print()
    return True


def report_completed_processes(completed: list[CompletedCliTask], *, summary: bool = False) -> None:
    """Report per-task outcome; raise ``typer.Exit(1)`` if any task failed.

    Delegates to :func:`report_completed_process` per item. Raises
    ``typer.Exit(1)`` when one or more tasks failed.

    Parameters
    ----------
    completed
        Output of :func:`run_concurrently`.
    summary
        Forwarded to :func:`report_completed_process`; suppresses per-task
        stdout/stderr dumps for a compact summary view.
    """
    console.flush()
    failed = False
    for item in completed:
        failed = report_completed_process(item.task.name, item.result, summary=summary) or failed
    if failed:
        raise typer.Exit(1)


def run_concurrently_with_report(
    tasks: list[CliTask],
    *,
    max_workers: int | None = None,
    dry_run: bool = False,
    env: dict[str, str] | None = None,
    summary: bool = False,
) -> None:
    """Run tasks concurrently and report outcomes.

    Convenience wrapper equivalent to::

        report_completed_processes(
            run_concurrently(tasks, max_workers=max_workers, dry_run=dry_run, env=env),
            summary=summary,
        )

    Raises ``typer.Exit(1)`` if any task failed.
    """
    report_completed_processes(
        run_concurrently(tasks, max_workers=max_workers, dry_run=dry_run, env=env),
        summary=summary,
    )
