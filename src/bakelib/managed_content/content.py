from collections.abc import Generator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import typer

from bake.ui import console

from .engine import (
    LOCK_FILE,
    ManagedContentError,
    ManagedFile,
    Plan,
    apply_plan,
    drop_detached,
    load_templates,
    plan_sync,
    read_lock,
    relock,
    write_lock,
)

EXIT_DRIFT = 1
EXIT_ERROR = 2


@contextmanager
def exit_on_error() -> Generator[None]:
    try:
        yield
    except ManagedContentError as e:
        console.error(str(e), markup=False)
        raise typer.Exit(EXIT_ERROR) from e


def _report_errors(plan: Plan) -> None:
    if not plan.errors:
        return
    for error in plan.errors:
        console.error(error, markup=False)
    console.error("nothing written", markup=False)
    raise typer.Exit(EXIT_ERROR)


@dataclass(frozen=True)
class ManagedContent:
    root: Path
    managed_files: Mapping[str, ManagedFile]
    values: Mapping[str, object]

    def lock(self, *, dry_run: bool, rebuild: bool = False) -> None:
        with exit_on_error():
            templates = load_templates(self.managed_files, self.values)
            try:
                locked = read_lock(self.root)
            except ManagedContentError:
                if not rebuild:
                    raise
                console.warning(f"{LOCK_FILE} does not parse, rebuilding it from the files")
                locked = {}
            locked, notes = drop_detached(locked, self.managed_files)
            for note in notes:
                console.warning(note, markup=False)
            entries = relock(self.root, templates, locked)
            if dry_run:
                return
            if write_lock(self.root, entries):
                console.success(f"{LOCK_FILE}: written", markup=False)

    def sync(self, *, dry_run: bool, force: bool) -> None:
        plan = self._plan(force=force)
        for note in plan.notes:
            console.warning(note, markup=False)
        if dry_run:
            for path in plan.writes:
                console.info(f"would write {path}", markup=False)
            for path in plan.deletes:
                console.info(f"would delete {path}", markup=False)
            return
        apply_plan(self.root, plan)
        for path in plan.writes:
            console.success(f"{path}: written", markup=False)
        for path in plan.deletes:
            console.success(f"{path}: deleted, no Space produces it", markup=False)
        if write_lock(self.root, plan.lock) and not plan.changes:
            console.success(f"{LOCK_FILE}: written", markup=False)
        if not plan.changes:
            console.success("managed content up to date")

    def check(self) -> None:
        plan = self._plan(force=False)
        if not plan.changes:
            console.success("managed content up to date")
            return
        for path in plan.writes:
            console.error(f"{path}: drift, differs from what its Spaces write now", markup=False)
        for path in plan.deletes:
            console.error(f"{path}: drift, no Space produces it any more", markup=False)
        console.error("run `bake mc sync` to update managed content", markup=False)
        raise typer.Exit(EXIT_DRIFT)

    def _plan(self, *, force: bool) -> Plan:
        with exit_on_error():
            templates = load_templates(self.managed_files, self.values)
            locked, notes = drop_detached(read_lock(self.root), self.managed_files)
            plan = plan_sync(self.root, templates, locked, force=force)
            plan.notes[:0] = notes
        _report_errors(plan)
        return plan
