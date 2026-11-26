import contextlib
import difflib
import importlib
import inspect
import os
import pkgutil
import subprocess
import tomllib
from collections import defaultdict
from collections.abc import Collection, Generator, Sequence
from dataclasses import dataclass
from functools import cache, cached_property
from importlib.resources import files
from pathlib import Path, PurePosixPath

from bake.cli.common.context import context
from bakelib.space.base import OXFMT_SUFFIXES, BaseSpace
from bakelib.space.utils import Fetch
from bakelib.space.utils.gitignore import Upstream

from .engine import LOCK_FILE, ManagedFile, load_templates

UPDATE_ENV = "BAKE_UPDATE_EXPECTED"
EXPECTED_SUFFIX = ".expected"
BLOCKS_SUFFIX = ".blocks" + EXPECTED_SUFFIX
UPDATE_HINT = f"rerun with {UPDATE_ENV}=1 to rewrite the expected files"
# renders offline: each github/gitignore template becomes one line naming it
STAND_IN_GITIGNORE = Upstream(
    latest_sha=lambda: "0" * 40,
    template=lambda _sha, path: f"# {path} template from github/gitignore\n",
)


@dataclass(frozen=True)
class TemplateCase:
    template: str
    path: str
    space: type[BaseSpace]
    managed_file: ManagedFile

    @property
    def expected_name(self) -> str:
        if self.managed_file.edited_text is None:
            return self.template
        return f"{self.template}@{self.space.__name__}"

    def __str__(self) -> str:
        return f"{self.expected_name}->{self.path}"


class TemplateSuite:
    def __init__(
        self,
        packages: Sequence[str],
        expected_dir: Path,
        gitignore_upstream: Upstream = STAND_IN_GITIGNORE,
        unused: Collection[str] = (),
    ) -> None:
        self.packages = tuple(packages)
        self.expected_dir = expected_dir
        self.gitignore_upstream = gitignore_upstream
        self.unused = frozenset(unused)

    def cases(self) -> list[TemplateCase]:
        return sorted(self._cases, key=str)

    def assert_all_templates_declared(self) -> None:
        declared = {case.template for case in self._cases if case.managed_file.text is None}
        on_disk = self._templates_on_disk()
        # Python modules in managed/ hold template strings, they are not templates themselves
        on_disk -= {t for t in on_disk - declared if t.endswith(".py")}
        problems = [f"{t}: no Space writes it" for t in sorted(on_disk - declared - self.unused)]
        problems += [
            f"{t}: listed as unused but a Space writes it or the file is missing"
            for t in sorted(self.unused - (on_disk - declared))
        ]
        problems += [
            f"{t}: a Space writes it but the file is missing" for t in sorted(declared - on_disk)
        ]
        if problems:
            raise AssertionError("\n".join(problems))

    def assert_no_stale_expected(self) -> None:
        declared = {case.expected_name for case in self._cases}
        stale = sorted(
            str(p.relative_to(self.expected_dir))
            for p in self.expected_dir.rglob(f"*{EXPECTED_SUFFIX}")
            if not _belongs_to(p.relative_to(self.expected_dir).as_posix(), declared)
        )
        if stale:
            raise AssertionError(f"delete the stale expected files in {self.expected_dir}: {stale}")

    def assert_renders(self, case: TemplateCase, project_dir: Path) -> None:
        actual = self._sync(case, project_dir)[case.path].decode()
        self._compare(
            f"{case.expected_name}{EXPECTED_SUFFIX}",
            actual,
            f"{case.path} written by {case.space.__name__}",
            UPDATE_HINT,
        )

    def assert_block_names(self, case: TemplateCase, project_dir: Path) -> None:
        with self._space_in(case, project_dir) as space:
            content = space._managed_content(Fetch.NEVER)
        template = load_templates({case.path: case.managed_file}, content.values)[case.path]
        self._compare(
            f"{case.expected_name}{BLOCKS_SUFFIX}",
            "".join(f"{name}\n" for name in template.blocks),
            f"editable blocks of {case.expected_name}",
            f"renaming an editable block drops every repo's edits to it; {UPDATE_HINT} "
            f"if the change is intended",
        )

    def _compare(self, expected_name: str, actual: str, actual_name: str, hint: str) -> None:
        expected_path = self.expected_dir / expected_name
        if os.environ.get(UPDATE_ENV) == "1":
            expected_path.parent.mkdir(parents=True, exist_ok=True)
            expected_path.write_text(actual)
        if not expected_path.is_file():
            raise AssertionError(f"{expected_path} is missing; {UPDATE_HINT}")
        expected = expected_path.read_text()
        if actual != expected:
            diff = difflib.unified_diff(
                expected.splitlines(keepends=True),
                actual.splitlines(keepends=True),
                fromfile=expected_name,
                tofile=actual_name,
            )
            raise AssertionError("".join(diff) + hint)

    def assert_clean_and_stable(self, case: TemplateCase, project_dir: Path) -> None:
        written = self._sync(case, project_dir)
        for number, line in enumerate(written[case.path].decode().splitlines(), 1):
            if line != line.rstrip():
                raise AssertionError(f"{case}: line {number} has trailing whitespace")
        if PurePosixPath(case.path).suffix.removeprefix(".") in OXFMT_SUFFIXES:
            # the Space's own oxfmt.config.ts is in the project, so oxfmt runs with it
            result = subprocess.run(
                ["oxfmt", "--check", case.path],
                cwd=project_dir,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                output = result.stdout + result.stderr
                raise AssertionError(f"{case}: oxfmt --check failed\n{output}")
        if self._sync(case, project_dir) != written:
            raise AssertionError(f"{case}: a second sync changed the project")
        self._assert_reads_back_to_defaults(case, project_dir)

    def _assert_reads_back_to_defaults(self, case: TemplateCase, project_dir: Path) -> None:
        # a template whose defaults split differently on reading would corrupt hand edits on sync
        (project_dir / LOCK_FILE).unlink()
        with self._space_in(case, project_dir) as space:
            space.managed_content_lock()
        lock = tomllib.loads((project_dir / LOCK_FILE).read_text())["managed-content"]
        if case.path not in lock:  # pragma: no cover
            raise AssertionError(f"{case}: the written file does not read back under its template")
        if changed := lock[case.path].get("editable"):
            raise AssertionError(
                f"{case}: editable blocks read back unlike their defaults: {changed}"
            )

    @cached_property
    def _cases(self) -> list[TemplateCase]:
        declared: dict[tuple[str, str, ManagedFile], set[type[BaseSpace]]] = defaultdict(set)
        for space_cls in self._spaces:
            for path, managed_file in _managed_files_of(space_cls).items():
                if (template := self._template_path(managed_file)) is not None:
                    declared[(template, path, managed_file)].add(space_cls)
        return [
            TemplateCase(template=template, path=path, space=owner, managed_file=managed_file)
            for (template, path, managed_file), spaces in declared.items()
            for owner in spaces
            # subclasses inherit the combination, so render through the Space that makes it
            if not any(other is not owner and issubclass(owner, other) for other in spaces)
        ]

    @cached_property
    def _spaces(self) -> list[type[BaseSpace]]:
        for package in self.packages:
            for module in pkgutil.walk_packages(_package_dirs(package), f"{package}."):
                # __main__ modules run their CLI on import
                if not module.name.endswith(".__main__"):
                    importlib.import_module(module.name)
        found: list[type[BaseSpace]] = []
        pending: list[type[BaseSpace]] = [BaseSpace]
        while pending:
            space_cls = pending.pop()
            pending.extend(space_cls.__subclasses__())
            if (
                space_cls not in found
                and space_cls.__module__ != __name__
                and space_cls.__module__.split(".")[0] in self.packages
            ):
                found.append(space_cls)
        return found

    def _template_path(self, managed_file: ManagedFile) -> str | None:
        if not managed_file.package or managed_file.package.split(".")[0] not in self.packages:
            return None
        template = Path(str(files(managed_file.package) / "managed" / managed_file.name)).resolve()
        (root,) = [
            package_dir.resolve().parent
            for package_dir in _package_dirs(managed_file.package.split(".")[0])
            if template.is_relative_to(package_dir.resolve())
        ]
        return template.relative_to(root).as_posix()

    def _templates_on_disk(self) -> set[str]:
        found: set[str] = set()
        for package in self.packages:
            for package_dir in _package_dirs(package):
                for managed_dir in package_dir.rglob("managed/"):
                    for path in managed_dir.rglob("*"):
                        if path.is_file() and "__pycache__" not in path.parts:
                            found.add(path.relative_to(package_dir.parent).as_posix())
        return found

    @contextlib.contextmanager
    def _space_in(self, case: TemplateCase, project_dir: Path) -> Generator[BaseSpace]:
        space = _offline(case.space, self.gitignore_upstream)(bake_manage_content=True)
        with contextlib.chdir(project_dir), context(chdir=project_dir, dry_run=False):
            yield space

    def _sync(self, case: TemplateCase, project_dir: Path) -> dict[str, bytes]:
        with self._space_in(case, project_dir) as space:
            space.managed_content_sync()
        return {
            p.relative_to(project_dir).as_posix(): p.read_bytes()
            for p in project_dir.rglob("*")
            if p.is_file()
        }


def _belongs_to(expected_name: str, templates: set[str]) -> bool:
    if (
        expected_name.endswith(BLOCKS_SUFFIX)
        and expected_name.removesuffix(BLOCKS_SUFFIX) in templates
    ):
        return True
    return expected_name.removesuffix(EXPECTED_SUFFIX) in templates


def _package_dirs(package: str) -> list[Path]:
    return [Path(p) for p in importlib.import_module(package).__path__]


@cache
def _concrete(space_cls: type[BaseSpace]) -> type[BaseSpace]:
    if not inspect.isabstract(space_cls):
        return space_cls
    stubs = {name: lambda *_, **__: None for name in space_cls.__abstractmethods__}
    return type(f"Concrete{space_cls.__name__}", (space_cls,), stubs)


@cache
def _offline(space_cls: type[BaseSpace], gitignore_upstream: Upstream) -> type[BaseSpace]:
    stubs = {"_get_gitignore_upstream": lambda _self: gitignore_upstream}
    return type(f"Offline{space_cls.__name__}", (_concrete(space_cls),), stubs)


def _managed_files_of(space_cls: type[BaseSpace]) -> dict[str, ManagedFile]:
    concrete = _concrete(space_cls)
    # skips construction, where some Spaces validate fields; a child's switch reads its default
    space = concrete.__new__(concrete)
    defaults = {
        name: info.get_default(call_default_factory=True)
        for name, info in concrete.model_fields.items()
    }
    object.__setattr__(space, "__dict__", defaults)
    return space._get_managed_files()
