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
    echo: bool = False


@dataclass(frozen=True, slots=True)
class CompletedCliTask:
    task: CliTask
    result: subprocess.CompletedProcess[str]


def spawn_env(cwd: Path | str | None = None, prepend_venv: bool = False) -> dict[str, str]:
    """Build a spawn-safe env dict for a child :class:`CliTask`.

    Clears ``VIRTUAL_ENV`` so a parent PEP723 script env does not leak
    into a spawned child ``bake`` process (which would load the wrong
    bakebook). When ``prepend_venv`` is set, prepends the child's
    ``.venv/bin`` to ``PATH`` so the child's subprocesses resolve the
    child's tools first.

    Parameters
    ----------
    cwd
        Child project directory. Used to locate ``.venv/bin``; only
        required when ``prepend_venv`` is set. Defaults to the current
        working directory.
    prepend_venv
        Prepend ``<cwd>/.venv/bin`` to ``PATH``. Default ``False``.
    """
    env: dict[str, str] = {"VIRTUAL_ENV": ""}
    if prepend_venv:
        base = os.getcwd() if cwd is None else os.path.abspath(cwd)
        venv_bin = os.path.join(base, ".venv", "bin")
        env["PATH"] = f"{venv_bin}:{os.environ['PATH']}"
    return env


def _run_cli_task(task: CliTask, *, dry_run: bool) -> subprocess.CompletedProcess[str]:
    # Concurrency-safe opts: stream off (no cross-thread interleave),
    # check off (siblings survive a failure);
    # echo per task (default off; name already shown by console.start).
    return run(
        task.command,
        cwd=task.cwd,
        dry_run=dry_run,
        env=task.env,
        stream=False,
        capture_output=True,
        check=False,
        echo=task.echo,
    )


def run_concurrently(
    tasks: list[CliTask],
    *,
    max_workers: int | None = None,
    dry_run: bool = False,
) -> list[CompletedCliTask]:
    """Run :class:`CliTask` instances concurrently via a thread pool.

    Thin concurrency wrapper over :func:`run`. ``run`` guards
    ``subprocess.Popen`` with a process-wide lock, so concurrent calls are
    safe.

    Each task runs with ``stream=False, capture_output=True, check=False``:
    streaming would interleave output across threads, and ``check=False``
    keeps one failed task from aborting its siblings. The caller owns
    exit-code policy (e.g. raising ``typer.Exit`` after inspecting
    ``returncode``). Env and echo are task-scoped: set ``CliTask.env`` and
    ``CliTask.echo`` per task (echo defaults to ``False`` — the task name
    is already shown by ``console.start``).

    Parameters
    ----------
    tasks
        Tasks to run. Order is preserved in the returned list.
    max_workers
        Thread cap. Defaults to ``min(len(tasks), os.cpu_count() or 4)``;
        an explicit value is clamped to ``len(tasks)``.
    dry_run
        Forwarded to :func:`run`; tasks print without executing.

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
        return CompletedCliTask(task=task, result=_run_cli_task(task, dry_run=dry_run))

    with ThreadPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(_run_task, tasks))


def report_completed_process(
    name: str,
    result: subprocess.CompletedProcess[str],
    *,
    show_fail_output: bool = True,
    show_success_output: bool = False,
) -> bool:
    """Report one process's outcome.

    Prints ``console.success(name)`` on success, or ``console.error(...)``
    on failure. Captured stdout/stderr is dumped when the matching flag is
    set and there is output to show.

    Returns ``True`` if the process failed.

    Parameters
    ----------
    show_fail_output
        When ``True`` (default), dump captured stdout/stderr on failure.
    show_success_output
        When ``True``, also dump captured stdout/stderr on success
        (default ``False`` keeps successful tasks quiet).
    """
    failed = result.returncode != 0
    if failed:
        console.error(f"{name} failed (exit {result.returncode})")
    else:
        console.success(name)
    should_dump = (failed and show_fail_output) or (not failed and show_success_output)
    # Separator closes the dump block; skip when nothing to dump.
    # if should_dump and (result.stdout or result.stderr):
    if should_dump and (result.stdout or result.stderr):
        _dump_output(result, name)
        _separator()
        console.err.print()
    return failed


def report_completed_processes(
    completed: list[CompletedCliTask],
    *,
    show_fail_output: bool = True,
    show_success_output: bool = False,
) -> None:
    """Report per-task outcome; raise ``typer.Exit(1)`` if any task failed.

    Delegates to :func:`report_completed_process` per item. Raises
    ``typer.Exit(1)`` when one or more tasks failed.

    Parameters
    ----------
    completed
        Output of :func:`run_concurrently`.
    show_fail_output
        Forwarded to :func:`report_completed_process`; dumps per-task
        stdout/stderr on failure (default ``True``).
    show_success_output
        Forwarded; also dumps on success (default ``False``).
    """
    console.flush()
    failed = False
    for item in completed:
        failed = (
            report_completed_process(
                item.task.name,
                item.result,
                show_fail_output=show_fail_output,
                show_success_output=show_success_output,
            )
            or failed
        )
    if failed:
        raise typer.Exit(1)


def run_concurrently_with_report(
    tasks: list[CliTask],
    *,
    max_workers: int | None = None,
    dry_run: bool = False,
    show_fail_output: bool = True,
    show_success_output: bool = False,
) -> None:
    """Run tasks concurrently and report outcomes.

    Convenience wrapper equivalent to::

        report_completed_processes(
            run_concurrently(tasks, max_workers=max_workers, dry_run=dry_run),
            show_fail_output=show_fail_output,
            show_success_output=show_success_output,
        )

    Raises ``typer.Exit(1)`` if any task failed.
    """
    report_completed_processes(
        run_concurrently(tasks, max_workers=max_workers, dry_run=dry_run),
        show_fail_output=show_fail_output,
        show_success_output=show_success_output,
    )
