import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import typer

from bake.ui import console
from bake.ui.run.main import CmdType, StrOrNoneCompletedProcess, dump_output, run


@dataclass(frozen=True, slots=True)
class CliTask:
    name: str
    command: CmdType
    cwd: Path | str | None = None
    env: dict[str, str] | None = None
    echo: bool = True


@dataclass(frozen=True, slots=True)
class CompletedCliTask:
    task: CliTask
    result: StrOrNoneCompletedProcess


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


class CliTaskRunner:
    def __init__(
        self,
        tasks: list[CliTask],
        *,
        dry_run: bool = False,
        show_count: bool = False,
        show_summary: bool = True,
    ) -> None:
        self.tasks = tasks
        self.dry_run = dry_run
        self.show_count = show_count
        self.show_summary = show_summary
        self.completed: list[CompletedCliTask] = []
        self._pos = {id(t): i for i, t in enumerate(tasks, 1)}
        self._completed_count = 0

    def run(self) -> None:
        self.completed: list[CompletedCliTask] = []
        self._completed_count = 0
        self._run_tasks()
        if self.dry_run:
            return
        if self.show_summary:
            self.summary()  # prints tally + recap, raises on failure
            return
        if self._tally()[1]:
            raise typer.Exit(1)

    def _run_tasks(self) -> None:
        raise NotImplementedError

    def begin(self, task: CliTask) -> None:
        console.start(f"Running {task.name}")

    def _report_task(self, task: CliTask, result: StrOrNoneCompletedProcess) -> None:
        if self.dry_run:
            return
        self._completed_count += 1
        self._status(task, result, with_count=True)

    def _labeled_name(self, task: CliTask) -> str:
        return f"[{self._completed_count}/{len(self.tasks)}] {task.name}"

    def summary(self) -> None:
        passed, failed = self._tally()
        if failed:
            tally = f"[green]{passed} passed[/green], [red]:x: {failed} failed[/red]"
        else:
            tally = f"[green]{passed} passed[/green]"
        title = f"Summary: {tally}"
        with console.block(
            title, line_style=console.BOLD_BLUE, title_mode="framed", end_title=False
        ):
            for item in self.completed:
                self._status(item.task, item.result)  # recap: no count (tally in title)
        if failed:
            raise typer.Exit(1)

    def _status(
        self, task: CliTask, result: StrOrNoneCompletedProcess, *, with_count: bool = False
    ) -> None:
        name = self._labeled_name(task) if (with_count and self.show_count) else task.name
        if result.returncode:
            console.error(f"{name} failed (exit {result.returncode})")
        else:
            console.success(name)

    def _tally(self) -> tuple[int, int]:
        failed = sum(1 for i in self.completed if i.result.returncode)
        passed = len(self.completed) - failed
        return passed, failed


class ParallelCliTaskRunner(CliTaskRunner):
    def __init__(
        self,
        tasks: list[CliTask],
        *,
        dry_run: bool = False,
        max_workers: int | None = None,
        show_fail_output: bool = True,
        show_success_output: bool = False,
        show_count: bool = False,
        show_summary: bool = True,
    ) -> None:
        super().__init__(tasks, dry_run=dry_run, show_count=show_count, show_summary=show_summary)
        self.max_workers = max_workers
        self.show_fail_output = show_fail_output
        self.show_success_output = show_success_output

    def _report_task(self, task: CliTask, result: StrOrNoneCompletedProcess) -> None:
        if self.dry_run:
            return
        self._completed_count += 1
        failed = result.returncode != 0
        should = (failed and self.show_fail_output) or (not failed and self.show_success_output)
        if not (should and (result.stdout or result.stderr)):
            self._status(task, result, with_count=True)
            return
        with console.block(
            task.name,
            line_style=console.BOLD_BLUE,
            title_mode="inline",
            start_label="START",
        ):
            dump_output(result)
            self._status(task, result, with_count=True)

    def _run_tasks(self) -> None:
        if not self.tasks:
            return
        workers = min(self.max_workers or (os.cpu_count() or 4), len(self.tasks))

        def _run(task: CliTask) -> StrOrNoneCompletedProcess:
            self.begin(task)  # START fires when a worker actually picks up the task
            # Concurrency-safe: stream off (no interleave), check off (siblings survive).
            return run(
                task.command,
                cwd=task.cwd,
                dry_run=self.dry_run,
                env=task.env,
                stream=False,
                capture_output=True,
                check=False,
                echo=task.echo,
            )

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(_run, task): task for task in self.tasks}
            for future in as_completed(futures):
                task = futures[future]
                result = future.result()
                self.completed.append(CompletedCliTask(task=task, result=result))
                self._report_task(task, result)
        self.completed.sort(key=lambda i: self._pos[id(i.task)])


class SequentialCliTaskRunner(CliTaskRunner):
    def _run_tasks(self) -> None:
        for i, task in enumerate(self.tasks):
            if i and not self.dry_run:  # live stream blurs START markers
                console.err.print()
            self.begin(task)
            result = run(
                task.command,
                cwd=task.cwd,
                dry_run=self.dry_run,
                env=task.env,
                stream=True,
                capture_output=False,
                check=False,
                echo=task.echo,
            )
            self.completed.append(CompletedCliTask(task=task, result=result))
            self._report_task(task, result)
