from pathlib import Path

import pytest

from bakelib.managed_content.testing import TemplateCase, TemplateSuite
from bakelib.space.utils.gitignore import Upstream

SNAPSHOT_DIR = Path(__file__).parent / "github_gitignore"
# templates downloaded once from github/gitignore at this commit, so the expected .gitignore is real
SNAPSHOT_SHA = "5e329a286aeb62cf9f7ffa6cf8721c4c3caae5b4"
GITHUB_GITIGNORE_SNAPSHOT = Upstream(
    latest_sha=lambda: SNAPSHOT_SHA,
    template=lambda _sha, path: (SNAPSHOT_DIR / f"{path}.gitignore").read_bytes().decode(),
)


SUITE = TemplateSuite(
    packages=["bake", "bakelib"],
    expected_dir=Path(__file__).parent / "expected",
    gitignore_upstream=GITHUB_GITIGNORE_SNAPSHOT,
    # kept for the Space that will write the GitHub Actions workflows
    unused=[
        "bakelib/space/managed/pre-commit.yml",
        "bakelib/space/managed/publish.yml",
        "bakelib/space/managed/test.yml",
    ],
)
CASES = SUITE.cases()


def test_templates_are_found() -> None:
    assert "bakelib/space/managed/oxfmt-config.ts" in {case.template for case in CASES}


def test_every_template_in_a_managed_folder_is_written_by_a_space() -> None:
    SUITE.assert_all_templates_declared()


def test_every_expected_file_belongs_to_a_template() -> None:
    SUITE.assert_no_stale_expected()


@pytest.mark.parametrize("case", CASES, ids=str)
def test_template_renders_to_its_expected_file(case: TemplateCase, tmp_path: Path) -> None:
    SUITE.assert_renders(case, tmp_path)


@pytest.mark.parametrize("case", CASES, ids=str)
def test_template_block_names_match_their_snapshot(case: TemplateCase, tmp_path: Path) -> None:
    SUITE.assert_block_names(case, tmp_path)


@pytest.mark.parametrize("case", CASES, ids=str)
def test_template_renders_clean_and_stable(case: TemplateCase, tmp_path: Path) -> None:
    SUITE.assert_clean_and_stable(case, tmp_path)
