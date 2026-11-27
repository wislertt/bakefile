import textwrap
import uuid
from dataclasses import dataclass
from pathlib import Path

import pytest

from bakelib.managed_content.testing import UPDATE_ENV, TemplateSuite

HEADER = 'managed by bakefile; edit only the parts marked "editable"'

KIT_SPACES = """
from bakelib.managed_content import ManagedFile
from bakelib.space.base import BaseSpace


class KitSpace(BaseSpace):
    def _get_managed_files(self) -> dict[str, ManagedFile]:
        return {
            **super()._get_managed_files(),
            "kit.yml": ManagedFile(__package__, "kit.yml"),
        }


class ChildKitSpace(KitSpace):
    pass
"""

TOOL_SPACES = """
from abc import abstractmethod

from bakelib.managed_content import ManagedFile
from bakelib.space.base import BaseSpace


class ToolSpace(BaseSpace):
    @abstractmethod
    def tool_name(self) -> str: ...

    def _get_managed_files(self) -> dict[str, ManagedFile]:
        return {**super()._get_managed_files(), "docs/lint.md": ManagedFile(__package__, "lint.md")}
"""


@dataclass
class Kit:
    name: str
    package_dir: Path
    expected_dir: Path
    suite: TemplateSuite

    def project(self, tmp_path: Path) -> Path:
        project = tmp_path / f"project-{uuid.uuid4().hex}"
        project.mkdir()
        return project


@pytest.fixture
def make_kit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    def make(kit_yml: str = "name: kit\n") -> Kit:
        name = f"kit_{uuid.uuid4().hex}"
        package_dir = tmp_path / "src" / name
        (package_dir / "managed").mkdir(parents=True)
        (package_dir / "__init__.py").write_text(textwrap.dedent(KIT_SPACES))
        (package_dir / "managed" / "kit.yml").write_text(kit_yml)
        (package_dir / "tools" / "managed").mkdir(parents=True)
        (package_dir / "tools" / "__init__.py").write_text(textwrap.dedent(TOOL_SPACES))
        (package_dir / "tools" / "managed" / "lint.md").write_text("# Lint\n")
        monkeypatch.syspath_prepend(str(tmp_path / "src"))
        expected_dir = tmp_path / "expected"
        return Kit(name, package_dir, expected_dir, TemplateSuite([name], expected_dir))

    return make


def _write_expected(kit: Kit, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with monkeypatch.context() as m:
        m.setenv(UPDATE_ENV, "1")
        for case in kit.suite.cases():
            kit.suite.assert_renders(case, kit.project(tmp_path))
            kit.suite.assert_block_names(case, kit.project(tmp_path))


def test_cases_cover_every_managed_folder_of_the_package_only(make_kit) -> None:
    kit = make_kit()

    cases = {str(case): case.space.__name__ for case in kit.suite.cases()}

    assert cases == {
        f"{kit.name}/managed/kit.yml->kit.yml": "KitSpace",
        f"{kit.name}/tools/managed/lint.md->docs/lint.md": "ToolSpace",
    }


def test_update_writes_the_expected_files_and_then_every_check_passes(
    make_kit, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kit = make_kit()

    _write_expected(kit, tmp_path, monkeypatch)

    assert (kit.expected_dir / kit.name / "managed" / "kit.yml.expected").read_text() == (
        f"# {HEADER}\nname: kit\n"
    )
    assert (kit.expected_dir / kit.name / "tools" / "managed" / "lint.md.expected").read_text() == (
        f"<!-- {HEADER} -->\n\n# Lint\n"
    )
    kit.suite.assert_all_templates_declared()
    kit.suite.assert_no_stale_expected()
    for case in kit.suite.cases():
        kit.suite.assert_renders(case, kit.project(tmp_path))
        kit.suite.assert_block_names(case, kit.project(tmp_path))
        kit.suite.assert_clean_and_stable(case, kit.project(tmp_path))


def test_missing_expected_file_fails_with_the_update_hint(make_kit, tmp_path: Path) -> None:
    kit = make_kit()
    case = kit.suite.cases()[0]

    with pytest.raises(AssertionError, match=f"is missing; rerun with {UPDATE_ENV}=1"):
        kit.suite.assert_renders(case, kit.project(tmp_path))


def test_changed_template_fails_with_a_diff(
    make_kit, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kit = make_kit()
    _write_expected(kit, tmp_path, monkeypatch)
    (kit.package_dir / "managed" / "kit.yml").write_text("name: renamed\n")
    (case,) = [c for c in kit.suite.cases() if c.path == "kit.yml"]

    with pytest.raises(AssertionError) as exc_info:
        kit.suite.assert_renders(case, kit.project(tmp_path))

    assert "-name: kit\n+name: renamed\n" in str(exc_info.value)


def test_template_no_space_writes_fails(make_kit) -> None:
    kit = make_kit()
    (kit.package_dir / "tools" / "managed" / "orphan.yml").write_text("x: 1\n")

    with pytest.raises(AssertionError, match=r"tools/managed/orphan\.yml: no Space writes it"):
        kit.suite.assert_all_templates_declared()


def test_template_listed_as_unused_may_stay_without_a_space(make_kit) -> None:
    kit = make_kit()
    (kit.package_dir / "tools" / "managed" / "later.yml").write_text("x: 1\n")
    suite = TemplateSuite(
        [kit.name], kit.expected_dir, unused=[f"{kit.name}/tools/managed/later.yml"]
    )

    suite.assert_all_templates_declared()


@pytest.mark.parametrize(
    "template", ["tools/managed/gone.yml", "managed/kit.yml"], ids=["missing", "written"]
)
def test_unused_entry_for_a_missing_or_written_template_fails(make_kit, template: str) -> None:
    kit = make_kit()
    suite = TemplateSuite([kit.name], kit.expected_dir, unused=[f"{kit.name}/{template}"])

    with pytest.raises(AssertionError, match=f"{template}: listed as unused"):
        suite.assert_all_templates_declared()


def test_declared_template_missing_from_disk_fails(make_kit) -> None:
    kit = make_kit()
    (kit.package_dir / "managed" / "kit.yml").unlink()

    with pytest.raises(AssertionError, match=r"managed/kit\.yml: a Space writes it but the file"):
        kit.suite.assert_all_templates_declared()


def test_stale_expected_file_fails(
    make_kit, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kit = make_kit()
    _write_expected(kit, tmp_path, monkeypatch)
    (kit.expected_dir / kit.name / "managed" / "gone.yml.expected").write_text("x: 1\n")

    with pytest.raises(AssertionError, match=r"stale expected files.*gone\.yml\.expected"):
        kit.suite.assert_no_stale_expected()


KIT_WITH_BLOCKS = (
    "name: kit\n# (editable) steps\n{% editable steps %}\nsteps: []\n{% endeditable %}\n"
    "# (editable) jobs\n{% editable jobs %}\n{% endeditable %}\n"
)


def _kit_case(kit: Kit):
    (case,) = [c for c in kit.suite.cases() if c.path == "kit.yml"]
    return case


def test_update_writes_a_block_name_snapshot_next_to_the_expected_file(
    make_kit, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kit = make_kit(kit_yml=KIT_WITH_BLOCKS)

    _write_expected(kit, tmp_path, monkeypatch)

    managed = kit.expected_dir / kit.name / "managed"
    assert (managed / "kit.yml.blocks.expected").read_text() == "steps\njobs\n"
    assert (
        kit.expected_dir / kit.name / "tools" / "managed" / "lint.md.blocks.expected"
    ).read_text() == ""
    kit.suite.assert_no_stale_expected()


def test_missing_block_name_snapshot_fails_with_the_update_hint(make_kit, tmp_path: Path) -> None:
    kit = make_kit(kit_yml=KIT_WITH_BLOCKS)

    with pytest.raises(
        AssertionError, match=f"blocks.expected is missing; rerun with {UPDATE_ENV}=1"
    ):
        kit.suite.assert_block_names(_kit_case(kit), kit.project(tmp_path))


def test_renamed_block_fails_against_its_snapshot_until_regenerated(
    make_kit, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kit = make_kit(kit_yml=KIT_WITH_BLOCKS)
    _write_expected(kit, tmp_path, monkeypatch)
    renamed = KIT_WITH_BLOCKS.replace("editable steps", "editable build_steps")
    (kit.package_dir / "managed" / "kit.yml").write_text(renamed)

    with pytest.raises(AssertionError) as exc_info:
        kit.suite.assert_block_names(_kit_case(kit), kit.project(tmp_path))
    _write_expected(kit, tmp_path, monkeypatch)

    message = str(exc_info.value)
    assert "-steps\n+build_steps\n" in message
    assert "drops every repo's edits" in message
    kit.suite.assert_block_names(_kit_case(kit), kit.project(tmp_path))


def test_stale_block_name_snapshot_fails(
    make_kit, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kit = make_kit()
    _write_expected(kit, tmp_path, monkeypatch)
    (kit.expected_dir / kit.name / "managed" / "gone.yml.blocks.expected").write_text("")

    with pytest.raises(AssertionError, match=r"stale expected files.*gone\.yml\.blocks\.expected"):
        kit.suite.assert_no_stale_expected()


def test_trailing_whitespace_fails(make_kit, tmp_path: Path) -> None:
    kit = make_kit(kit_yml="name: kit  \n")
    (case,) = [c for c in kit.suite.cases() if c.path == "kit.yml"]

    with pytest.raises(AssertionError, match="line 2 has trailing whitespace"):
        kit.suite.assert_clean_and_stable(case, kit.project(tmp_path))


def test_unformatted_template_fails_oxfmt(make_kit, tmp_path: Path) -> None:
    kit = make_kit(kit_yml="name:    kit\n")
    (case,) = [c for c in kit.suite.cases() if c.path == "kit.yml"]

    with pytest.raises(AssertionError, match="oxfmt --check failed"):
        kit.suite.assert_clean_and_stable(case, kit.project(tmp_path))


def test_template_whose_defaults_do_not_read_back_fails(make_kit, tmp_path: Path) -> None:
    # the first block's default holds the fixed line after it, so reading splits it differently
    kit = make_kit(
        kit_yml=(
            "{% editable a %}\na: 1\n#\n{% endeditable %}\n#\n{% editable b %}\n{% endeditable %}\n"
        ),
    )
    (case,) = [c for c in kit.suite.cases() if c.path == "kit.yml"]

    with pytest.raises(AssertionError, match="editable blocks read back unlike their defaults"):
        kit.suite.assert_clean_and_stable(case, kit.project(tmp_path))


FLAKY_SPACES = """
from pathlib import Path

from bakelib.managed_content import ManagedFile
from bakelib.space.base import BaseSpace


class FlakySpace(BaseSpace):
    def _get_managed_files(self) -> dict[str, ManagedFile]:
        template = "b.yml" if Path("flaky.yml").exists() else "a.yml"
        return {**super()._get_managed_files(), "flaky.yml": ManagedFile(__package__, template)}
"""


def test_space_whose_output_changes_between_syncs_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    name = f"flaky_{uuid.uuid4().hex}"
    package_dir = tmp_path / "src" / name
    (package_dir / "managed").mkdir(parents=True)
    (package_dir / "__init__.py").write_text(textwrap.dedent(FLAKY_SPACES))
    (package_dir / "managed" / "a.yml").write_text("a: 1\n")
    (package_dir / "managed" / "b.yml").write_text("b: 1\n")
    monkeypatch.syspath_prepend(str(tmp_path / "src"))
    suite = TemplateSuite([name], tmp_path / "expected")
    (case,) = suite.cases()
    project = tmp_path / "project"
    project.mkdir()

    with pytest.raises(AssertionError, match="a second sync changed the project"):
        suite.assert_clean_and_stable(case, project)


KIT_WITH_HOOK = (
    "name: kit\njobs:\n    {% hook extra_jobs %}\n    # (editable) more jobs below\n"
    "{% editable jobs %}\n{% endeditable %}\n"
)
CHILD_SPACES = """
from bakelib.managed_content import ManagedFile

from . import KitSpace
from .managed.snippets import LINT_JOB


class JobKitSpace(KitSpace):
    lint_job: bool = True

    def _get_managed_files(self) -> dict[str, ManagedFile]:
        files = super()._get_managed_files()
        if self.lint_job:
            files["kit.yml"] = files["kit.yml"].insert("extra_jobs", LINT_JOB)
        return files


class JobKitChild(JobKitSpace):
    pass


class StringKitSpace(KitSpace):
    def _get_managed_files(self) -> dict[str, ManagedFile]:
        managed_file = ManagedFile.from_text(
            "name: from-string\\n", package=__package__, name="str.yml"
        )
        return {**super()._get_managed_files(), "str.yml": managed_file}
"""
SNIPPETS = '''
LINT_JOB = """\\
lint:
    runs-on: {% editable lint_runs_on %}ubuntu-latest{% endeditable %} # (editable)

"""
'''


@pytest.fixture
def child_kit(make_kit) -> Kit:
    kit = make_kit(kit_yml=KIT_WITH_HOOK)
    (kit.package_dir / "children.py").write_text(textwrap.dedent(CHILD_SPACES))
    (kit.package_dir / "managed" / "snippets.py").write_text(textwrap.dedent(SNIPPETS))
    return kit


def test_child_combination_is_its_own_case_with_its_own_expected_file(
    child_kit: Kit, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kit = child_kit

    cases = {str(case): case.space.__name__ for case in kit.suite.cases()}
    _write_expected(kit, tmp_path, monkeypatch)

    assert cases == {
        f"{kit.name}/managed/kit.yml->kit.yml": "KitSpace",
        f"{kit.name}/managed/kit.yml@JobKitSpace->kit.yml": "JobKitSpace",
        f"{kit.name}/managed/str.yml->str.yml": "StringKitSpace",
        f"{kit.name}/tools/managed/lint.md->docs/lint.md": "ToolSpace",
    }
    managed = kit.expected_dir / kit.name / "managed"
    assert (managed / "kit.yml@JobKitSpace.expected").read_text() == (
        f"# {HEADER}\nname: kit\njobs:\n    lint:\n        runs-on: ubuntu-latest # (editable)\n"
        "\n    # (editable) more jobs below\n"
    )
    assert (managed / "kit.yml@JobKitSpace.blocks.expected").read_text() == "lint_runs_on\njobs\n"
    assert (managed / "kit.yml.blocks.expected").read_text() == "jobs\n"
    assert (managed / "str.yml.expected").read_text() == f"# {HEADER}\nname: from-string\n"
    kit.suite.assert_no_stale_expected()
    for case in kit.suite.cases():
        kit.suite.assert_renders(case, kit.project(tmp_path))
        kit.suite.assert_block_names(case, kit.project(tmp_path))


def test_python_modules_in_managed_are_not_templates_and_string_templates_need_no_file(
    child_kit: Kit,
) -> None:
    child_kit.suite.assert_all_templates_declared()


def test_stale_expected_file_of_a_gone_combination_fails(
    child_kit: Kit, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kit = child_kit
    _write_expected(kit, tmp_path, monkeypatch)
    (kit.expected_dir / kit.name / "managed" / "kit.yml@GoneSpace.expected").write_text("")

    with pytest.raises(AssertionError, match=r"stale expected files.*kit\.yml@GoneSpace\.expected"):
        kit.suite.assert_no_stale_expected()
