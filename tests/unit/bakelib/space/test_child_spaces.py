import re
import tomllib
from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

import pytest

from bake import Context
from bake.cli.common.context import context
from bake.ui.logger import strip_ansi
from bakelib.managed_content import ManagedContentError, ManagedFile
from bakelib.space.base import BaseSpace
from tests.unit.bakelib.space import managed_fixtures
from tests.utils.cli import exit_code

HEADER = 'managed by bakefile; edit only the parts marked "editable"'
FIXTURES = managed_fixtures.__name__
CI = "ci.yml"

PARENT = f"""# {HEADER}
name: hooks
on:
    # (editable)
    push:

jobs:
    build:
        runs-on: ubuntu-latest # (editable)
        steps:
            - run: build
            # (editable) more build steps

    # (editable) more jobs below
"""

LINT_JOB = """\
lint:
    runs-on: {% editable lint_runs_on %}ubuntu-latest{% endeditable %} # (editable)
    steps:
        # (editable) pin
        - uses: actions/checkout@{% editable lint_checkout %}aaaa # v1{% endeditable %}
        {% hook lint_steps %}
        - run: lint

"""
DOCS_JOB = """\
docs:
    runs-on: ubuntu-latest
    # (editable)
{% editable docs_env %}
    env: {}
{% endeditable %}

"""
LINT_RENDERED = """\
    lint:
        runs-on: ubuntu-latest # (editable)
        steps:
            # (editable) pin
            - uses: actions/checkout@aaaa # v1
            - run: lint

"""
DOCS_RENDERED = (
    "    docs:\n        runs-on: ubuntu-latest\n        # (editable)\n        env: {}\n\n"
)
JOBS_TAIL = "    # (editable) more jobs below\n"


class ParentSpace(BaseSpace):
    bake_manage_content: bool = True
    template: str = "hooks.yml"

    def _get_managed_files(self) -> dict[str, ManagedFile]:
        return {CI: ManagedFile(FIXTURES, self.template)}


class StringParentSpace(BaseSpace):
    bake_manage_content: bool = True

    def _get_managed_files(self) -> dict[str, ManagedFile]:
        text = (Path(managed_fixtures.__file__).parent / "managed" / "hooks.yml").read_text()
        return {CI: ManagedFile.from_text(text, package=FIXTURES, name="hooks.yml")}


class LintChild(ParentSpace):
    def _get_managed_files(self) -> dict[str, ManagedFile]:
        files = super()._get_managed_files()
        files[CI] = files[CI].insert("extra_jobs", LINT_JOB)
        return files


class DocsChild(ParentSpace):
    docs_job: bool = True

    def _get_managed_files(self) -> dict[str, ManagedFile]:
        files = super()._get_managed_files()
        if self.docs_job:
            files[CI] = files[CI].insert("extra_jobs", DOCS_JOB)
        return files


class LintThenDocs(DocsChild, LintChild):
    pass


class DocsThenLint(LintChild, DocsChild):
    pass


class GrandChild(LintChild):
    def _get_managed_files(self) -> dict[str, ManagedFile]:
        files = super()._get_managed_files()
        files[CI] = files[CI].insert("lint_steps", "- run: grandchild\n")
        return files


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def ctx(project: Path) -> Context:
    return context(chdir=project, dry_run=False)


def _sync(space: BaseSpace, project: Path) -> str:
    space.managed_content_sync()
    return (project / CI).read_text()


class TestInsert:
    def test_template_hooks_render_to_nothing(self, ctx: Context, project: Path) -> None:
        with ctx:
            assert _sync(ParentSpace(), project) == PARENT

    def test_insert_lands_above_the_hook_indented_to_its_column(
        self, ctx: Context, project: Path
    ) -> None:
        with ctx:
            written = _sync(LintChild(), project)

        assert written == PARENT.replace(JOBS_TAIL, LINT_RENDERED + JOBS_TAIL)

    @pytest.mark.parametrize(
        ("space", "jobs"),
        [
            pytest.param(LintThenDocs, LINT_RENDERED + DOCS_RENDERED, id="lint-then-docs"),
            pytest.param(DocsThenLint, DOCS_RENDERED + LINT_RENDERED, id="docs-then-lint"),
        ],
    )
    def test_inserts_from_two_children_land_in_mro_order(
        self, ctx: Context, project: Path, space: type[BaseSpace], jobs: str
    ) -> None:
        with ctx:
            written = _sync(space(), project)

        assert written == PARENT.replace(JOBS_TAIL, jobs + JOBS_TAIL)

    def test_grandchild_inserts_at_a_hook_its_parents_insert_brings(
        self, ctx: Context, project: Path
    ) -> None:
        with ctx:
            written = _sync(GrandChild(), project)

        assert "            - run: grandchild\n            - run: lint\n" in written

    def test_childs_switch_turns_its_insert_off(self, ctx: Context, project: Path) -> None:
        with ctx:
            assert _sync(DocsChild(docs_job=False), project) == PARENT

    def test_string_template_renders_like_the_same_file_under_the_same_key(
        self, ctx: Context, project: Path
    ) -> None:
        with ctx:
            written = _sync(StringParentSpace(), project)

        assert written == PARENT
        assert _lock(project)["template"] == ParentSpace()._get_managed_files()[CI].key


def _lock(project: Path) -> dict:
    return tomllib.loads((project / "bake.lock").read_text())["managed-content"][CI]


def _child(change: Callable[[ManagedFile], ManagedFile]) -> type[ParentSpace]:
    class Child(ParentSpace):
        def _get_managed_files(self) -> dict[str, ManagedFile]:
            files = super()._get_managed_files()
            files[CI] = change(files[CI])
            return files

    return Child


class TestSetDefault:
    def test_replaces_a_block_default(self, ctx: Context, project: Path) -> None:
        space = _child(lambda f: f.set_default("events", "    pull_request:\n"))
        with ctx:
            written = _sync(space(), project)

        assert written == PARENT.replace("    push:\n", "    pull_request:\n")
        assert "editable" not in _lock(project)

    def test_replaces_an_inline_block_default(self, ctx: Context, project: Path) -> None:
        space = _child(lambda f: f.set_default("build_runs_on", "macos-latest\n"))
        with ctx:
            written = _sync(space(), project)

        assert written == PARENT.replace("ubuntu-latest", "macos-latest")


LINT_RUNS_ON = "    lint:\n        runs-on: ubuntu-latest"
BUMPED = "actions/checkout@bbbb # v2"


class TestEditsInsideAnInsert:
    def _edit_and_bump(self, project: Path) -> str:
        path = project / CI
        text = path.read_text().replace("actions/checkout@aaaa # v1", BUMPED)
        path.write_text(text.replace(LINT_RUNS_ON, LINT_RUNS_ON.replace("ubuntu", "macos")))
        return path.read_text()

    def test_repo_edit_and_bump_kept_across_sync_and_locked(
        self, ctx: Context, project: Path
    ) -> None:
        with ctx:
            _sync(LintChild(), project)
            edited = self._edit_and_bump(project)
            written = _sync(LintChild(), project)

        assert written == edited
        assert _lock(project)["editable"] == {
            "lint_checkout": "bbbb # v2",
            "lint_runs_on": "macos-latest",
        }

    def test_repo_edit_and_bump_kept_across_an_upgrade(self, ctx: Context, project: Path) -> None:
        with ctx:
            _sync(LintChild(), project)
            edited = self._edit_and_bump(project)
            _sync(LintChild(), project)
            written = _sync(LintChild(template="hooks_v2.yml"), project)

        assert written == edited.replace("- run: build\n", "- run: build --all\n")
        assert "macos-latest" in written
        assert BUMPED in written


MISTAKES = [
    pytest.param(
        lambda f: f.insert("extra_job", DOCS_JOB),
        "there is no template hook 'extra_job'",
        id="unknown-hook",
    ),
    pytest.param(
        lambda f: f.insert("extra_jobs", LINT_JOB).insert("extra_jobs", LINT_JOB),
        "adds editable block 'lint_checkout', which the template already has",
        id="repeated-block",
    ),
    pytest.param(
        lambda f: f.insert("extra_jobs", "{% hook build_steps %}\n"),
        "template hook 'build_steps' appears twice",
        id="repeated-hook",
    ),
    pytest.param(
        lambda f: f.set_default("event", ""),
        "there is no editable block 'event'",
        id="unknown-block",
    ),
    pytest.param(
        lambda f: f.set_default("build_steps", "- run: test\n"),
        "editable block 'build_steps' holds template hook 'build_steps'",
        id="default-over-hook",
    ),
    pytest.param(
        lambda f: f.set_default("build_runs_on", "a\nb\n"),
        "editable block 'build_runs_on' is inline, so its default must be one line",
        id="inline-default-two-lines",
    ),
]


class TestMistakes:
    @pytest.mark.parametrize(("change", "message"), MISTAKES)
    def test_raises_at_the_childs_call_with_the_template_key(
        self, change: Callable[[ManagedFile], ManagedFile], message: str
    ) -> None:
        parent = ManagedFile(FIXTURES, "hooks.yml")

        with pytest.raises(ManagedContentError, match=re.escape(message)) as exc_info:
            change(parent)

        assert str(exc_info.value).startswith(f"template {parent.key}: ")

    def test_set_default_on_an_unclosed_block_raises(self) -> None:
        parent = ManagedFile.from_text(
            "{% editable build %}\n- run: x\n", package=FIXTURES, name="unclosed.yml"
        )

        with pytest.raises(
            ManagedContentError,
            match=re.escape("editable block 'build' needs `{% endeditable %}` to close it"),
        ):
            parent.set_default("build", "- run: y\n")

    @pytest.mark.parametrize(("change", "message"), MISTAKES)
    @pytest.mark.parametrize("command", ["sync", "lint"])
    def test_command_exits_2_with_nothing_written(
        self,
        ctx: Context,
        project: Path,
        capsys: pytest.CaptureFixture,
        change: Callable[[ManagedFile], ManagedFile],
        message: str,
        command: str,
    ) -> None:
        space = _child(change)()
        with ctx, patch.object(ctx, "run"):
            code = exit_code(space.managed_content_sync if command == "sync" else space.lint)

        assert code == 2
        assert list(project.iterdir()) == []
        assert message in strip_ansi(capsys.readouterr().err)


class TestTemplateHookGrammar:
    def test_hook_that_appears_twice_fails_at_load(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        text = "a: 1\n{% hook more %}\nb: 1\n{% hook more %}\n"

        class TwiceSpace(ParentSpace):
            def _get_managed_files(self) -> dict[str, ManagedFile]:
                return {CI: ManagedFile.from_text(text, package=FIXTURES, name="twice.yml")}

        with ctx:
            code = exit_code(TwiceSpace().managed_content_sync)

        assert code == 2
        assert list(project.iterdir()) == []
        assert "template hook 'more' appears twice" in strip_ansi(capsys.readouterr().err)

    def test_hook_not_alone_on_its_line_is_a_malformed_tag(
        self, ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        class InlineHookSpace(ParentSpace):
            def _get_managed_files(self) -> dict[str, ManagedFile]:
                return {
                    CI: ManagedFile.from_text(
                        "a: {% hook more %}\n", package=FIXTURES, name="inline.yml"
                    )
                }

        with ctx:
            code = exit_code(InlineHookSpace().managed_content_sync)

        assert code == 2
        assert "malformed tag" in strip_ansi(capsys.readouterr().err)
