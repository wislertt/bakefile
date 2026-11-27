import hashlib
import json
import re
import shlex
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner
from typing_extensions import override

from bake import Context
from bake.cli.common.context import context
from bake.ui.logger import strip_ansi
from bakelib.managed_content import ManagedContentError, ManagedFile
from bakelib.managed_content.engine import _distribution
from bakelib.refreshable_cache.fnox import FNOX_LOCAL_FILE, _ensure_gitignored
from bakelib.space.base import BaseSpace
from bakelib.space.github import GitHubActionsTools, ZervGitHubActionsTools
from bakelib.space.python import PythonSpace
from bakelib.space.python_lib import PythonLibSpace
from bakelib.space.rust import RustSpace
from bakelib.space.utils import Fetch
from bakelib.space.utils.gitignore import TemplateNotFoundError, Upstream, read_section
from tests.unit.bakelib.space import managed_fixtures
from tests.utils.cli import exit_code

HEADER = 'managed by bakefile; edit only the parts marked "editable"'
DETACH_HINT = (
    "to keep it as is, call `.detach()` on its entry in `_get_managed_files()` in bakefile.py"
)
OXFMT_CONFIG = Path(__file__).parents[4] / "oxfmt.config.ts"
OXFMT_EXPECTED = (
    Path(__file__).parents[1]
    / "managed_content/expected/bakelib/space/managed/oxfmt-config.ts.expected"
)


FIXTURES = managed_fixtures.__name__


class ManagedSpace(BaseSpace):
    bake_manage_content: bool = True


class OxfmtSpace(ManagedSpace):
    def _get_managed_files(self) -> dict[str, ManagedFile]:
        return {"oxfmt.config.ts": super()._get_managed_files()["oxfmt.config.ts"]}


class TwoFileSpace(ManagedSpace):
    def _get_managed_files(self) -> dict[str, ManagedFile]:
        return {**super()._get_managed_files(), "notes.md": ManagedFile(FIXTURES, "notes.md")}


class FixtureSpace(BaseSpace):
    bake_manage_content: bool = True
    template: str = "v1.ts"

    def _get_managed_files(self) -> dict[str, ManagedFile]:
        return {"config.ts": ManagedFile(FIXTURES, self.template)}


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def ctx(project: Path) -> Context:
    return context(chdir=project, dry_run=False)


def _sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


class TestSyncFresh:
    def test_writes_oxfmt_config_with_header_and_locks_it(
        self, ctx: Context, project: Path
    ) -> None:
        with ctx:
            ManagedSpace().managed_content_sync()

        written = (project / "oxfmt.config.ts").read_text()
        assert written == OXFMT_EXPECTED.read_text()
        lock = tomllib.loads((project / "bake.lock").read_text())
        assert lock["version"] == 1
        assert lock["revision"] == 1
        assert lock["managed-content"]["oxfmt.config.ts"] == {
            "template": "bakelib.space:oxfmt-config.ts",
            "hash": _sha(written),
        }


class TestSyncUpToDate:
    def test_second_sync_changes_nothing(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        with ctx:
            ManagedSpace().managed_content_sync()
            before = {p: p.stat().st_mtime_ns for p in project.iterdir()}
            capsys.readouterr()
            ManagedSpace().managed_content_sync()

        assert {p: p.stat().st_mtime_ns for p in project.iterdir()} == before
        assert "managed content up to date" in strip_ansi(capsys.readouterr().err)

    @pytest.mark.parametrize(
        "variant",
        [
            pytest.param(lambda t: t.replace("\n", "\r\n"), id="crlf"),
            pytest.param(lambda t: "\ufeff" + t, id="bom"),
            pytest.param(lambda t: t.removesuffix("\n"), id="no-final-newline"),
        ],
    )
    def test_line_ending_variants_are_not_drift_and_not_rewritten(
        self, ctx: Context, project: Path, variant
    ) -> None:
        config = project / "oxfmt.config.ts"
        with ctx:
            ManagedSpace().managed_content_sync()
            config.write_bytes(variant(config.read_text()).encode())
            before = config.read_bytes()
            ManagedSpace().managed_content_sync()
            with ctx.override_dry_run(True):
                ManagedSpace().lint()

        assert config.read_bytes() == before


class TestToggle:
    def test_off_by_default_setup_dev_and_lint_touch_nothing(
        self, mock_ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        with mock_ctx:
            BaseSpace().setup_dev(fast=2)
            BaseSpace().lint()

        assert list(project.iterdir()) == []
        err = strip_ansi(capsys.readouterr().err)
        assert "managed" not in err
        assert "bake.lock" not in err

    @pytest.mark.parametrize("command", ["managed_content_sync", "managed_content_lock"])
    def test_off_commands_exit_nonzero_with_hint(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture, command: str
    ) -> None:
        with ctx, pytest.raises(typer.Exit) as exc_info:
            getattr(BaseSpace(), command)()

        assert exc_info.value.exit_code != 0
        assert "BAKE_MANAGE_CONTENT=true" in strip_ansi(capsys.readouterr().err)
        assert list(project.iterdir()) == []

    def test_env_var_turns_it_on(
        self, ctx: Context, project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("BAKE_MANAGE_CONTENT", "true")
        with ctx:
            BaseSpace().managed_content_sync()

        assert (project / "oxfmt.config.ts").exists()
        assert (project / "bake.lock").exists()


def _sync_exit_code(space: BaseSpace, **kwargs: bool) -> int:
    return exit_code(lambda: space.managed_content_sync(**kwargs))


def _lint_exit_code(space: BaseSpace, ctx: Context) -> int:
    with patch.object(ctx, "run"):
        return exit_code(space.lint)


def _snapshot(project: Path) -> dict[str, bytes]:
    return {str(p.relative_to(project)): p.read_bytes() for p in project.rglob("*") if p.is_file()}


class TestSyncErrors:
    def test_edit_in_fixed_text_exits_2_naming_the_line_and_writes_nothing(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        config = project / "oxfmt.config.ts"
        with ctx:
            ManagedSpace().managed_content_sync()
            config.write_text(config.read_text().replace("semi: false", "semi: true"))
            before = _snapshot(project)
            capsys.readouterr()
            code = _sync_exit_code(ManagedSpace())

        assert code == 2
        assert _snapshot(project) == before
        err = strip_ansi(capsys.readouterr().err)
        assert "expected '    semi: false,', but line 3 is '    semi: true,'" in err
        assert DETACH_HINT in err
        assert "nothing written" in err

    def test_force_overwrites_an_edit_in_fixed_text(self, ctx: Context, project: Path) -> None:
        config = project / "oxfmt.config.ts"
        with ctx:
            ManagedSpace().managed_content_sync()
            expected = config.read_text()
            config.write_text(expected.replace("semi: false", "semi: true"))
            ManagedSpace().managed_content_sync(force=True)

        assert config.read_text() == expected

    def test_headerless_file_exits_2_and_force_replaces_it(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        config = project / "oxfmt.config.ts"
        config.write_text("export default {}\n")
        with ctx:
            code = _sync_exit_code(ManagedSpace())
            assert config.read_text() == "export default {}\n"
            assert not (project / "bake.lock").exists()
            ManagedSpace().managed_content_sync(force=True)

        assert code == 2
        err = strip_ansi(capsys.readouterr().err)
        assert "without the managed header" in err
        assert DETACH_HINT in err
        assert config.read_text().startswith(f"// {HEADER}\n")

    def test_locked_file_with_header_missing_is_an_error(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        config = project / "oxfmt.config.ts"
        with ctx:
            ManagedSpace().managed_content_sync()
            config.write_text(config.read_text().split("\n", 1)[1])
            before = _snapshot(project)
            code = _sync_exit_code(ManagedSpace())

        assert code == 2
        assert _snapshot(project) == before
        err = strip_ansi(capsys.readouterr().err)
        assert "header missing on a file bake.lock manages" in err
        assert DETACH_HINT not in err

    @pytest.mark.parametrize(
        ("edit", "message"),
        [
            pytest.param(
                lambda t: t.rsplit("\n", 2)[0] + "\n",
                "expected '}', but the file ends at line 3",
                id="file-shorter",
            ),
            pytest.param(
                lambda t: t + "// extra\n",
                "expected the end of the file, but line 5 is '// extra'",
                id="file-longer",
            ),
        ],
    )
    def test_edit_message_names_where_the_file_length_differs(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture, edit, message: str
    ) -> None:
        config = project / "config.ts"
        with ctx:
            FixtureSpace().managed_content_sync()
            config.write_text(edit(config.read_text()))
            capsys.readouterr()
            code = _sync_exit_code(FixtureSpace())

        assert code == 2
        assert message in strip_ansi(capsys.readouterr().err)

    def test_edit_message_splits_lines_only_at_newlines(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        config = project / "config.ts"
        with ctx:
            FixtureSpace().managed_content_sync()
            config.write_text(config.read_text().replace("{\n", "{\x0c\n"))
            capsys.readouterr()
            code = _sync_exit_code(FixtureSpace())

        assert code == 2
        err = strip_ansi(capsys.readouterr().err)
        # the console drops the form feed, so the line shows without it
        assert "expected 'export default {', but line 2 is 'export default {'" in err

    def test_unlocked_file_with_an_edit_in_fixed_text_exits_2_without_the_upgrade_hint(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        (project / "oxfmt.config.ts").write_text(
            OXFMT_CONFIG.read_text().replace("semi: false", "semi: true")
        )
        with ctx:
            code = _sync_exit_code(ManagedSpace())

        assert code == 2
        err = strip_ansi(capsys.readouterr().err)
        assert "expected '    semi: false,', but line 3 is '    semi: true,'" in err
        assert "bake mc sync --force" in err
        assert DETACH_HINT in err
        assert "changed since" not in err
        assert not (project / "bake.lock").exists()

    def test_file_that_is_not_utf8_is_an_error(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        (project / "oxfmt.config.ts").write_bytes(b"\xff\xfe not text")
        with ctx:
            code = _sync_exit_code(ManagedSpace())

        assert code == 2
        assert "oxfmt.config.ts: not UTF-8 text" in strip_ansi(capsys.readouterr().err)
        assert not (project / "bake.lock").exists()

    def test_one_error_writes_no_file(self, ctx: Context, project: Path) -> None:
        (project / "notes.md").write_bytes(b"# hand notes\n")
        with ctx:
            code = _sync_exit_code(TwoFileSpace())

        assert code == 2
        assert _snapshot(project) == {"notes.md": b"# hand notes\n"}

    def test_dry_run_writes_nothing(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        with ctx:
            ManagedSpace().managed_content_sync(dry_run=True)

        assert list(project.iterdir()) == []
        assert "would write oxfmt.config.ts" in strip_ansi(capsys.readouterr().err)


class TestSyncLockOnly:
    def test_file_already_matching_is_locked_without_rewriting(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        config = project / "oxfmt.config.ts"
        config.write_text(OXFMT_CONFIG.read_text())
        before = config.stat().st_mtime_ns
        with ctx:
            OxfmtSpace().managed_content_sync()

        assert config.stat().st_mtime_ns == before
        assert "oxfmt.config.ts" in (project / "bake.lock").read_text()
        err = strip_ansi(capsys.readouterr().err)
        assert "bake.lock: written" in err
        assert "managed content up to date" in err


class TestDroppedFile:
    def test_file_no_space_produces_is_deleted_and_hand_file_later_left_alone(
        self, ctx: Context, project: Path
    ) -> None:
        with ctx:
            TwoFileSpace().managed_content_sync()
            assert (project / "notes.md").exists()
            ManagedSpace().managed_content_sync()
            assert not (project / "notes.md").exists()
            assert "notes.md" not in (project / "bake.lock").read_text()

            (project / "notes.md").write_text("# my own notes\n")
            ManagedSpace().managed_content_sync()

        assert (project / "notes.md").read_text() == "# my own notes\n"

    def test_file_changed_since_locked_is_kept_with_a_note_and_unlocked(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        notes = project / "notes.md"
        with ctx:
            TwoFileSpace().managed_content_sync()
            notes.write_text(notes.read_text() + "my hand edit\n")
            edited = notes.read_bytes()
            capsys.readouterr()
            ManagedSpace().managed_content_sync()
            first = strip_ansi(capsys.readouterr().err)
            ManagedSpace().managed_content_sync()
            second = strip_ansi(capsys.readouterr().err)

        assert notes.read_bytes() == edited
        assert "notes.md" not in (project / "bake.lock").read_text()
        assert (
            "notes.md: kept, changed since bake wrote it and no Space produces it any more; "
            "it is now a hand file"
        ) in first
        assert "deleted" not in first
        assert "notes.md" not in second

    def test_file_deleted_by_hand_only_loses_its_lock_entry(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        with ctx:
            TwoFileSpace().managed_content_sync()
            (project / "notes.md").unlink()
            capsys.readouterr()
            ManagedSpace().managed_content_sync()

        assert not (project / "notes.md").exists()
        assert "notes.md" not in (project / "bake.lock").read_text()
        assert "notes.md" not in strip_ansi(capsys.readouterr().err)

    def test_file_no_longer_utf8_is_kept_as_changed(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        notes = project / "notes.md"
        with ctx:
            TwoFileSpace().managed_content_sync()
            notes.write_bytes(b"\xff\xfe not utf-8\n")
            capsys.readouterr()
            ManagedSpace().managed_content_sync()

        assert notes.read_bytes() == b"\xff\xfe not utf-8\n"
        assert "notes.md" not in (project / "bake.lock").read_text()
        assert "notes.md: kept, changed since bake wrote it" in strip_ansi(capsys.readouterr().err)

    def test_force_keeps_a_changed_file_too(self, ctx: Context, project: Path) -> None:
        notes = project / "notes.md"
        with ctx:
            TwoFileSpace().managed_content_sync()
            notes.write_text(notes.read_text() + "my hand edit\n")
            edited = notes.read_bytes()
            ManagedSpace().managed_content_sync(force=True)

        assert notes.read_bytes() == edited
        assert "notes.md" not in (project / "bake.lock").read_text()

    def test_dry_run_lists_only_files_it_would_delete(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        notes = project / "notes.md"
        with ctx:
            TwoFileSpace().managed_content_sync()
            notes.write_text(notes.read_text() + "my hand edit\n")
            lock_before = (project / "bake.lock").read_text()
            capsys.readouterr()
            ManagedSpace().managed_content_sync(dry_run=True)

        err = strip_ansi(capsys.readouterr().err)
        assert "would delete" not in err
        assert "notes.md: kept" in err
        assert (project / "bake.lock").read_text() == lock_before

    def test_dry_run_reports_the_delete_and_keeps_the_file(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        with ctx:
            TwoFileSpace().managed_content_sync()
            capsys.readouterr()
            ManagedSpace().managed_content_sync(dry_run=True)

        assert (project / "notes.md").exists()
        assert "would delete notes.md" in strip_ansi(capsys.readouterr().err)

    def test_lint_reports_it_as_drift(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        with ctx:
            TwoFileSpace().managed_content_sync()
            capsys.readouterr()
            with patch.object(ctx, "run"), pytest.raises(typer.Exit) as exc_info:
                ManagedSpace().lint()

        assert exc_info.value.exit_code == 1
        assert (project / "notes.md").exists()
        assert "notes.md: drift, no Space produces it any more" in strip_ansi(
            capsys.readouterr().err
        )


class DetachableSpace(FixtureSpace):
    detached: bool = False

    def _get_managed_files(self) -> dict[str, ManagedFile]:
        files = super()._get_managed_files()
        if self.detached:
            files["config.ts"] = files["config.ts"].detach()
        return files


DETACHED_NOTE = "config.ts: detached, bake no longer manages it; its bake.lock entry is dropped"


def _edit_fixed_text(config: Path) -> bytes:
    config.write_text(config.read_text().replace("value: 1", "value: 3"))
    return config.read_bytes()


class TestDetachedFile:
    def test_sync_keeps_a_fixed_text_edit_and_drops_the_lock_entry_with_a_note_once(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        config = project / "config.ts"
        with ctx:
            DetachableSpace().managed_content_sync()
            edited = _edit_fixed_text(config)
            capsys.readouterr()
            DetachableSpace(detached=True).managed_content_sync()
            first = strip_ansi(capsys.readouterr().err)
            DetachableSpace(detached=True).managed_content_sync()
            second = strip_ansi(capsys.readouterr().err)

        assert config.read_bytes() == edited
        assert "config.ts" not in (project / "bake.lock").read_text()
        assert DETACHED_NOTE in first
        assert "deleted" not in first
        assert "config.ts" not in second

    def test_lint_reports_no_drift_and_drops_the_lock_entry_with_a_note_once(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        config = project / "config.ts"
        with ctx:
            DetachableSpace().managed_content_sync()
            edited = _edit_fixed_text(config)
            capsys.readouterr()
            first_code = _lint_exit_code(DetachableSpace(detached=True), ctx)
            first = strip_ansi(capsys.readouterr().err)
            second_code = _lint_exit_code(DetachableSpace(detached=True), ctx)
            second = strip_ansi(capsys.readouterr().err)

        assert (first_code, second_code) == (0, 0)
        assert config.read_bytes() == edited
        assert "config.ts" not in (project / "bake.lock").read_text()
        assert DETACHED_NOTE in first
        assert "config.ts" not in second

    def test_setup_dev_keeps_a_fixed_text_edit(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        config = project / "config.ts"
        with ctx:
            DetachableSpace().managed_content_sync()
            edited = _edit_fixed_text(config)
            capsys.readouterr()
            with patch.object(ctx, "run"):
                DetachableSpace(detached=True).setup_dev(fast=2)

        assert config.read_bytes() == edited
        assert "config.ts" not in (project / "bake.lock").read_text()
        assert DETACHED_NOTE in strip_ansi(capsys.readouterr().err)

    def test_update_keeps_a_fixed_text_edit(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        config = project / "config.ts"
        with ctx:
            DetachableSpace().managed_content_sync()
            edited = _edit_fixed_text(config)
            capsys.readouterr()
            with patch.object(ctx, "run"):
                DetachableSpace(detached=True).update(fast=2)
            # stands in for the `bake post-update` subprocess update runs last
            DetachableSpace(detached=True).post_update()

        assert config.read_bytes() == edited
        assert "config.ts" not in (project / "bake.lock").read_text()
        assert strip_ansi(capsys.readouterr().err).count(DETACHED_NOTE) == 1

    def test_path_with_no_file_gets_nothing_written(self, ctx: Context, project: Path) -> None:
        with ctx:
            DetachableSpace(detached=True).managed_content_sync()
            code = _lint_exit_code(DetachableSpace(detached=True), ctx)

        assert code == 0
        assert not (project / "config.ts").exists()

    def test_missing_template_does_not_block(self, ctx: Context, project: Path) -> None:
        config = project / "config.ts"
        with ctx:
            DetachableSpace().managed_content_sync()
            edited = _edit_fixed_text(config)
            missing = DetachableSpace(template="missing.ts", detached=True)
            sync_code = _sync_exit_code(missing)
            force_code = _sync_exit_code(missing, force=True)
            lint_code = _lint_exit_code(missing, ctx)

        assert (sync_code, force_code, lint_code) == (0, 0, 0)
        assert config.read_bytes() == edited

    def test_reattached_file_that_still_matches_keeps_its_blocks_and_is_locked(
        self, ctx: Context, project: Path
    ) -> None:
        ci = project / "ci.yml"
        with ctx:
            DetachableBlocksSpace().managed_content_sync()
            bumped = ci.read_text().replace("version: 1.0", "version: 1.1")
            ci.write_text(bumped)
            DetachableBlocksSpace(detached=True).managed_content_sync()
            assert "ci.yml" not in (project / "bake.lock").read_text()
            DetachableBlocksSpace().managed_content_sync()

        assert ci.read_text() == bumped
        assert _lock_entry(project, "ci.yml")["editable"] == {"version": "1.1"}

    def test_reattached_file_with_a_fixed_text_edit_exits_2_and_force_writes_the_template(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        config = project / "config.ts"
        with ctx:
            DetachableSpace().managed_content_sync()
            expected = config.read_text()
            DetachableSpace(detached=True).managed_content_sync()
            edited = _edit_fixed_text(config)
            capsys.readouterr()
            code = _sync_exit_code(DetachableSpace())
            assert config.read_bytes() == edited
            DetachableSpace().managed_content_sync(force=True)

        assert code == 2
        assert "bake mc sync --force" in strip_ansi(capsys.readouterr().err)
        assert config.read_text() == expected
        assert "config.ts" in (project / "bake.lock").read_text()


class TestUpgrade:
    def test_template_change_with_current_lock_rewrites_the_file(
        self, ctx: Context, project: Path
    ) -> None:
        with ctx:
            FixtureSpace(template="v1.ts").managed_content_sync()
            FixtureSpace(template="v2.ts").managed_content_sync()

        assert (
            project / "config.ts"
        ).read_text() == f"// {HEADER}\nexport default {{\n    value: 2,\n}}\n"
        assert 'template = "' in (project / "bake.lock").read_text()
        assert ":v2.ts" in (project / "bake.lock").read_text()

    def test_template_change_with_unlocked_edit_exits_2(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        config = project / "config.ts"
        with ctx:
            FixtureSpace(template="v1.ts").managed_content_sync()
            config.write_text(config.read_text().replace("value: 1", "value: 3"))
            code = _sync_exit_code(FixtureSpace(template="v2.ts"))

        assert code == 2
        assert "expected '    value: 2,', but line 3 is '    value: 3,'" in strip_ansi(
            capsys.readouterr().err
        )


class TestLock:
    def test_unparsable_lock_exits_2_with_mc_lock_hint(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        (project / "bake.lock").write_text("<<<<<<< HEAD\n")
        with ctx:
            code = _sync_exit_code(ManagedSpace())

        assert code == 2
        assert "bake mc lock" in strip_ansi(capsys.readouterr().err)
        assert not (project / "oxfmt.config.ts").exists()

    def test_mc_lock_rebuilds_an_unparsable_lock_from_the_files(
        self, ctx: Context, project: Path
    ) -> None:
        with ctx:
            ManagedSpace().managed_content_sync()
            good = (project / "bake.lock").read_text()
            (project / "bake.lock").write_text("<<<<<<< HEAD\n")
            ManagedSpace().managed_content_lock()

        assert (project / "bake.lock").read_text() == good

    def test_mc_lock_records_a_file_that_reads_without_writing_it(
        self, ctx: Context, project: Path
    ) -> None:
        config = project / "oxfmt.config.ts"
        config.write_text(OXFMT_CONFIG.read_text())
        with ctx:
            ManagedSpace().managed_content_lock()

        lock = tomllib.loads((project / "bake.lock").read_text())
        assert lock["managed-content"]["oxfmt.config.ts"]["hash"] == _sha(config.read_text())

    @pytest.mark.parametrize(
        ("lock", "message"),
        [
            pytest.param("version = 2\n", "unsupported version 2", id="version"),
            pytest.param(
                "version = 1\nmanaged-content = 1\n", "`managed-content` is not a table", id="table"
            ),
            pytest.param(
                'version = 1\n[managed-content."a.ts"]\ntemplate = "bakefile:a.ts"\n',
                "entry 'a.ts' needs string `template` and `hash`",
                id="entry",
            ),
            pytest.param(
                'version = 1\n[managed-content."a.ts"]\ntemplate = "bakefile:a.ts"\n'
                'hash = "sha256:0"\neditable.a = 1\n',
                "entry 'a.ts' needs string `editable` values",
                id="editable",
            ),
        ],
    )
    def test_malformed_lock_exits_2_with_mc_lock_hint(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture, lock: str, message: str
    ) -> None:
        (project / "bake.lock").write_text(lock)
        with ctx:
            code = _sync_exit_code(ManagedSpace())

        assert code == 2
        err = strip_ansi(capsys.readouterr().err)
        assert message in err
        assert "bake mc lock" in err
        assert not (project / "oxfmt.config.ts").exists()

    def test_lint_does_not_rebuild_an_unparsable_lock(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        (project / "bake.lock").write_text("<<<<<<< HEAD\n")
        with ctx, patch.object(ctx, "run"), pytest.raises(typer.Exit) as exc_info:
            ManagedSpace().lint()

        assert exc_info.value.exit_code == 2
        assert "bake mc lock" in strip_ansi(capsys.readouterr().err)
        assert (project / "bake.lock").read_text() == "<<<<<<< HEAD\n"


OXFMT_CMD = 'oxfmt "**/'


class TestLint:
    @pytest.mark.usefixtures("project")
    def test_drift_exits_1_before_oxfmt_runs(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        with mock_ctx, pytest.raises(typer.Exit) as exc_info:
            ManagedSpace().lint()

        assert exc_info.value.exit_code == 1
        err = strip_ansi(capsys.readouterr().err)
        assert "oxfmt.config.ts: drift" in err
        assert "bake mc sync" in err
        assert OXFMT_CMD not in err

    def test_clean_checks_drift_then_runs_oxfmt(
        self, ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        with ctx:
            ManagedSpace().managed_content_sync()
            capsys.readouterr()
            with ctx.override_dry_run(True):
                ManagedSpace().lint()

        err = strip_ansi(capsys.readouterr().err)
        assert err.index("managed content up to date") < err.index(OXFMT_CMD)

    def test_error_exits_2(
        self, mock_ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        (project / "oxfmt.config.ts").write_text("export default {}\n")
        with mock_ctx, pytest.raises(typer.Exit) as exc_info:
            ManagedSpace().lint()

        assert exc_info.value.exit_code == 2
        assert OXFMT_CMD not in strip_ansi(capsys.readouterr().err)

    def test_relocks_a_stale_lock(self, ctx: Context, project: Path) -> None:
        (project / "oxfmt.config.ts").write_text(OXFMT_CONFIG.read_text())
        with ctx, patch.object(ctx, "run"):
            OxfmtSpace().lint()

        assert "oxfmt.config.ts" in (project / "bake.lock").read_text()


class TestSetupDev:
    def test_syncs_before_the_clean_that_may_remove_the_venv_bake_runs_from(
        self, mock_ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        with mock_ctx:
            ManagedSpace().setup_dev(fast=2)

        err = strip_ansi(capsys.readouterr().err)
        assert err.index("would write oxfmt.config.ts") < err.index("Cleaning")
        assert err.index("Cleaning") < err.index("pre-commit install")
        assert list(project.iterdir()) == []

    def test_writes_managed_files(self, ctx: Context, project: Path) -> None:
        with ctx, patch.object(ctx, "run"):
            ManagedSpace().setup_dev(fast=2)

        assert (project / "oxfmt.config.ts").read_text().startswith(f"// {HEADER}\n")
        assert (project / "bake.lock").exists()


class TestHookComposition:
    def test_most_derived_space_wins_a_path(self, ctx: Context, project: Path) -> None:
        class OverrideSpace(ManagedSpace):
            def _get_managed_files(self) -> dict[str, ManagedFile]:
                return {
                    **super()._get_managed_files(),
                    "oxfmt.config.ts": ManagedFile(FIXTURES, "v1.ts"),
                }

        with ctx:
            OverrideSpace().managed_content_sync()

        assert (project / "oxfmt.config.ts").read_text() == (
            f"// {HEADER}\nexport default {{\n    value: 1,\n}}\n"
        )

    def test_diamond_collects_every_branch_once(self, ctx: Context, project: Path) -> None:
        class LeftSpace(ManagedSpace):
            def _get_managed_files(self) -> dict[str, ManagedFile]:
                return {**super()._get_managed_files(), "left.ts": ManagedFile(FIXTURES, "v1.ts")}

        class RightSpace(ManagedSpace):
            def _get_managed_files(self) -> dict[str, ManagedFile]:
                return {**super()._get_managed_files(), "right.ts": ManagedFile(FIXTURES, "v2.ts")}

        class DiamondSpace(LeftSpace, RightSpace):
            pass

        with ctx:
            DiamondSpace().managed_content_sync()

        lock = tomllib.loads((project / "bake.lock").read_text())
        assert sorted(lock["managed-content"]) == [
            ".gitignore",
            "left.ts",
            "oxfmt.config.ts",
            "right.ts",
        ]


def _single_file_space(path: str, template: str) -> BaseSpace:
    class SingleFileSpace(ManagedSpace):
        def _get_managed_files(self) -> dict[str, ManagedFile]:
            return {path: ManagedFile(FIXTURES, template)}

    return SingleFileSpace()


class TestTemplates:
    @pytest.mark.parametrize(
        ("path", "template", "header"),
        [
            (".gitignore", "ignore", f"# {HEADER}"),
            (".dockerignore", "ignore", f"# {HEADER}"),
            ("config.yml", "fixed.yml", f"# {HEADER}"),
            ("config.ts", "v1.ts", f"// {HEADER}"),
            ("docs/notes.md", "notes.md", f"<!-- {HEADER} -->"),
        ],
    )
    def test_header_uses_the_file_types_comment_syntax(
        self, ctx: Context, project: Path, path: str, template: str, header: str
    ) -> None:
        with ctx:
            _single_file_space(path, template).managed_content_sync()

        assert (project / path).read_text().split("\n", 1)[0] == header

    @pytest.mark.parametrize(
        ("path", "template", "message"),
        [
            ("config.json", "plain.json", "plain .json has no comments"),
            ("notes.txt", "notes.md", "unsupported file type"),
            ("missing.ts", "missing.ts", "not found"),
        ],
    )
    def test_template_load_error_exits_2_and_writes_nothing(
        self,
        ctx: Context,
        project: Path,
        capsys: pytest.CaptureFixture,
        path: str,
        template: str,
        message: str,
    ) -> None:
        with ctx:
            code = _sync_exit_code(_single_file_space(path, template))

        assert code == 2
        assert message in strip_ansi(capsys.readouterr().err)
        assert list(project.iterdir()) == []

    def test_managed_file_without_a_package_exits_2(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        class NoPackageSpace(ManagedSpace):
            def _get_managed_files(self) -> dict[str, ManagedFile]:
                return {"config.ts": ManagedFile(None, "v1.ts")}

        with ctx:
            code = _sync_exit_code(NoPackageSpace())

        assert code == 2
        assert (
            "template v1.ts: give ManagedFile a package, or use ManagedFile.from_text"
            in strip_ansi(capsys.readouterr().err)
        )
        assert list(project.iterdir()) == []

    def test_managed_file_from_a_package_that_cannot_be_imported_exits_2(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        class MissingPackageSpace(ManagedSpace):
            def _get_managed_files(self) -> dict[str, ManagedFile]:
                return {"config.ts": ManagedFile("mc_no_such_pkg", "v1.ts")}

        with ctx:
            code = _sync_exit_code(MissingPackageSpace())

        assert code == 2
        assert "template mc_no_such_pkg:v1.ts: package 'mc_no_such_pkg' cannot be imported" in (
            strip_ansi(capsys.readouterr().err)
        )
        assert list(project.iterdir()) == []


def _make_package(root: Path, name: str) -> None:
    (root / name).mkdir(parents=True)
    (root / name / "__init__.py").write_text("")


def _make_dist_info(site: Path, dist: str, direct_url: dict) -> None:
    info = site / f"{dist.replace('-', '_')}-1.0.dist-info"
    info.mkdir(parents=True)
    (info / "METADATA").write_text(f"Metadata-Version: 2.1\nName: {dist}\nVersion: 1.0\n")
    (info / "direct_url.json").write_text(json.dumps(direct_url))


class TestTemplateKey:
    def test_key_is_the_package_and_name_as_written(self) -> None:
        assert ManagedFile("bakelib.space", "x.ts").key == "bakelib.space:x.ts"

    def test_text_with_package_and_name_keys_like_a_file(self) -> None:
        assert ManagedFile.from_text("a\n", package="pkg.sub", name="x.ts").key == "pkg.sub:x.ts"

    def test_text_without_package_and_name_keys_as_the_repo(self) -> None:
        managed_file = ManagedFile.from_text("a\n")
        assert (managed_file.key, managed_file.key_for("x.ts")) == ("repo", "repo:x.ts")

    def test_text_with_only_package_or_name_raises(self) -> None:
        with pytest.raises(ManagedContentError, match="give both package and name, or neither"):
            ManagedFile.from_text("a\n", package="pkg")


class TestUpgradeHintDistribution:
    def test_installed_package_uses_its_distribution_name(self) -> None:
        assert _distribution("typer") == "typer"

    def test_editable_package_uses_the_distribution_installed_from_its_source(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        source = tmp_path / "src"
        _make_package(source, "mc_editable_pkg")
        site = tmp_path / "site"
        _make_dist_info(
            site, "editable-dist", {"url": source.as_uri(), "dir_info": {"editable": True}}
        )
        monkeypatch.syspath_prepend(str(site))
        monkeypatch.syspath_prepend(str(source))
        monkeypatch.delitem(sys.modules, "mc_editable_pkg", raising=False)

        assert _distribution("mc_editable_pkg.sub") == "editable-dist"

    def test_non_editable_install_from_its_source_is_not_matched(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        source = tmp_path / "src"
        _make_package(source, "mc_local_pkg")
        _make_dist_info(tmp_path / "site", "local-dist", {"url": source.as_uri(), "dir_info": {}})
        monkeypatch.syspath_prepend(str(tmp_path / "site"))
        monkeypatch.syspath_prepend(str(source))
        monkeypatch.delitem(sys.modules, "mc_local_pkg", raising=False)

        assert _distribution("mc_local_pkg") == "mc_local_pkg"

    def test_package_from_no_distribution_uses_its_top_level_name(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _make_package(tmp_path, "mc_orphan_pkg")
        monkeypatch.syspath_prepend(str(tmp_path))
        monkeypatch.delitem(sys.modules, "mc_orphan_pkg", raising=False)

        assert _distribution("mc_orphan_pkg") == "mc_orphan_pkg"

    def test_package_that_cannot_be_imported_uses_its_top_level_name(self) -> None:
        assert _distribution("mc_missing_pkg.sub") == "mc_missing_pkg"


class TestCommandGroup:
    @pytest.mark.parametrize("group", ["managed-content", "mc"])
    def test_sync_reachable_from_group_and_alias(self, project: Path, group: str) -> None:
        space = ManagedSpace()
        obj = context(chdir=project).obj
        result = CliRunner().invoke(space._app, [group, "sync"], obj=obj)

        assert result.exit_code == 0, result.output
        assert (project / "oxfmt.config.ts").exists()

    def test_alias_is_hidden_from_help(self) -> None:
        result = CliRunner().invoke(ManagedSpace()._app, ["--help"])

        assert "managed-content" in result.output
        assert " mc " not in result.output

    def test_sync_help_lists_refresh(self) -> None:
        result = CliRunner().invoke(ManagedSpace()._app, ["mc", "sync", "--help"])

        assert "--refresh" in strip_ansi(result.output)

    @pytest.mark.parametrize("path", ["../outside.ts", "/tmp/outside.ts", "C:/outside.ts"])
    def test_lock_path_outside_the_project_is_an_error(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture, path: str
    ) -> None:
        (project / "bake.lock").write_text(
            f'version = 1\nrevision = 1\n\n[managed-content."{path}"]\n'
            'template = "bakefile:x.ts"\nhash = "sha256:0"\n'
        )
        with ctx:
            code = _sync_exit_code(ManagedSpace())

        assert code == 2
        assert "outside the project" in strip_ansi(capsys.readouterr().err)
        assert not (project / "oxfmt.config.ts").exists()


class BlocksSpace(BaseSpace):
    bake_manage_content: bool = True
    template: str = "blocks_v1.yml"

    def _get_managed_files(self) -> dict[str, ManagedFile]:
        return {"ci.yml": ManagedFile(FIXTURES, self.template)}


class DetachableBlocksSpace(BlocksSpace):
    detached: bool = False

    def _get_managed_files(self) -> dict[str, ManagedFile]:
        files = super()._get_managed_files()
        if self.detached:
            files["ci.yml"] = files["ci.yml"].detach()
        return files


BLOCKS_V1 = f"""# {HEADER}
name: fixture
# (editable) version
version: 1.0
# (editable) jobs
jobs:
    - build
# (editable) extra
end: true
"""


def _lock_entry(project: Path, path: str) -> dict:
    return tomllib.loads((project / "bake.lock").read_text())["managed-content"][path]


class TestEditableBlocks:
    def test_fresh_sync_writes_defaults_and_locks_no_editable_blocks(
        self, ctx: Context, project: Path
    ) -> None:
        with ctx:
            BlocksSpace().managed_content_sync()

        assert (project / "ci.yml").read_text() == BLOCKS_V1
        assert "editable" not in _lock_entry(project, "ci.yml")

    def test_edit_inside_blocks_leaves_the_file_and_locks_the_blocks(
        self, ctx: Context, project: Path
    ) -> None:
        ci = project / "ci.yml"
        with ctx:
            BlocksSpace().managed_content_sync()
            edited = (
                BLOCKS_V1.replace("version: 1.0", "version: 1.5")
                .replace("    - build\n", "    - build\n    - deploy\n")
                .replace("# (editable) extra\n", "# (editable) extra\nmore: 1\n")
            )
            ci.write_text(edited)
            BlocksSpace().managed_content_sync()

        assert ci.read_text() == edited
        assert _lock_entry(project, "ci.yml")["editable"] == {
            "version": "1.5",
            "jobs": "jobs:\n    - build\n    - deploy\n",
            "extra": "more: 1\n",
        }

    def test_force_on_a_locked_file_missing_its_header_keeps_the_locked_blocks(
        self, ctx: Context, project: Path
    ) -> None:
        ci = project / "ci.yml"
        edited = BLOCKS_V1.replace("version: 1.0", "version: 1.5")
        with ctx:
            BlocksSpace().managed_content_sync()
            ci.write_text(edited)
            BlocksSpace().managed_content_lock()
            ci.write_text(edited.split("\n", 1)[1])
            BlocksSpace().managed_content_sync(force=True)

        assert ci.read_text() == edited

    def test_locked_block_without_a_final_newline_is_written_on_its_own_lines(
        self, ctx: Context, project: Path
    ) -> None:
        ci = project / "ci.yml"
        edited = BLOCKS_V1.replace("    - build\n", "    - build\n    - deploy\n")
        lock = project / "bake.lock"
        with ctx:
            BlocksSpace().managed_content_sync()
            ci.write_text(edited)
            BlocksSpace().managed_content_lock()
            # a hand-edited lock can drop the newline a multi-line block always ends with
            lock.write_text(lock.read_text().replace('- deploy\\n"', '- deploy"'))
            ci.unlink()
            BlocksSpace().managed_content_sync()

        assert ci.read_text() == edited


TEMPLATE_PACKAGE = "mc_template_fixtures"


@pytest.fixture
def make_template(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path_factory.mktemp("templates")
    (root / TEMPLATE_PACKAGE / "managed").mkdir(parents=True)
    (root / TEMPLATE_PACKAGE / "__init__.py").write_text("")
    monkeypatch.syspath_prepend(str(root))
    monkeypatch.delitem(sys.modules, TEMPLATE_PACKAGE, raising=False)

    def make(text: str, name: str = "t.yml") -> str:
        (root / TEMPLATE_PACKAGE / "managed" / name).write_text(text)
        return name

    return make


def _template_space(path: str, name: str) -> BaseSpace:
    class TemplateSpace(ManagedSpace):
        def _get_managed_files(self) -> dict[str, ManagedFile]:
            return {path: ManagedFile(TEMPLATE_PACKAGE, name)}

    return TemplateSpace()


class TestTemplateGrammarErrors:
    @pytest.mark.parametrize(
        ("path", "template", "message"),
        [
            pytest.param(
                "t.yml",
                "a: {%editable x %}1{% endeditable %}\n",
                "malformed tag near '{%editable x",
                id="near-miss-spacing",
            ),
            pytest.param(
                "t.yml",
                "a: {% editible x %}1{% endeditable %}\n",
                "malformed tag",
                id="near-miss-word",
            ),
            pytest.param(
                "t.yml",
                "a: {% editable x %}1\n",
                "needs `{% endeditable %}`",
                id="unclosed",
            ),
            pytest.param(
                "t.yml",
                "a: {% editable x %}1{% endeditable y %}\n",
                "needs `{% endeditable %}`",
                id="wrong-close-name",
            ),
            pytest.param(
                "t.yml",
                "a: {% editable x %}1{% endeditible %}\n",
                "malformed tag near '{% endeditible",
                id="near-miss-close",
            ),
            pytest.param(
                "t.yml",
                "a: 1\n{% endeditable %}\n",
                "malformed tag",
                id="stray-close",
            ),
            pytest.param(
                "t.yml",
                "a:\n{% editable x %}\n  1{% endeditable %}\n",
                "both tags on their own lines",
                id="half-block",
            ),
            pytest.param(
                "t.yml",
                "a: {% editable x %}1{% endeditable %}{% editable y %}2{% endeditable %}\n",
                "editable block 'y' needs fixed text between",
                id="adjacent",
            ),
            pytest.param(
                "t.yml",
                "a: {% editable x %}1{% endeditable %}\nb: {% editable x %}2{% endeditable %}\n",
                "editable block 'x' appears twice",
                id="duplicate",
            ),
            pytest.param(
                ".gitignore",
                "{% editable x adopt %}\n{% endeditable %}\n",
                "malformed tag near '{% editable x adopt %}",
                id="adopt-option",
            ),
            pytest.param(
                "t.yml",
                "a: {{ bakefile.name }}\n",
                "bakefile value 'name' is not among the values the Bakebook gives",
                id="value-not-given",
            ),
        ],
    )
    def test_load_error_exits_2_and_writes_nothing(
        self,
        ctx: Context,
        project: Path,
        capsys: pytest.CaptureFixture,
        make_template,
        path: str,
        template: str,
        message: str,
    ) -> None:
        name = make_template(template, name="t" + Path(path).suffix)
        with ctx:
            code = _sync_exit_code(_template_space(path, name))

        assert code == 2
        assert message in strip_ansi(capsys.readouterr().err)
        assert list(project.iterdir()) == []

    def test_github_expressions_are_fixed_text(
        self, ctx: Context, project: Path, make_template
    ) -> None:
        name = make_template("run: ${{ github.sha }}\n")
        with ctx:
            _template_space("ci.yml", name).managed_content_sync()

        assert (project / "ci.yml").read_text() == f"# {HEADER}\nrun: ${{{{ github.sha }}}}\n"


BLOCKS_V2 = f"""# {HEADER}
name: fixture-v2
# (editable) version
version: 2.0
# (editable) jobs
jobs:
    - build
    - test
end: true
"""


class TestEditableUpgrade:
    def test_untouched_blocks_take_the_new_default(self, ctx: Context, project: Path) -> None:
        with ctx:
            BlocksSpace(template="blocks_v1.yml").managed_content_sync()
            BlocksSpace(template="blocks_v2.yml").managed_content_sync()

        assert (project / "ci.yml").read_text() == BLOCKS_V2

    def test_emptied_block_stays_empty_and_edit_is_kept(self, ctx: Context, project: Path) -> None:
        ci = project / "ci.yml"
        with ctx:
            BlocksSpace(template="blocks_v1.yml").managed_content_sync()
            ci.write_text(
                BLOCKS_V1.replace("jobs:\n    - build\n", "").replace("1.0", "1.0-pinned")
            )
            BlocksSpace(template="blocks_v1.yml").managed_content_lock()
            BlocksSpace(template="blocks_v2.yml").managed_content_sync()

        assert ci.read_text() == BLOCKS_V2.replace("jobs:\n    - build\n    - test\n", "").replace(
            "2.0", "1.0-pinned"
        )
        assert _lock_entry(project, "ci.yml")["editable"] == {"jobs": "", "version": "1.0-pinned"}

    def test_block_gone_from_the_template_is_dropped_with_a_note(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        ci = project / "ci.yml"
        with ctx:
            BlocksSpace(template="blocks_v1.yml").managed_content_sync()
            ci.write_text(BLOCKS_V1.replace("end: true", "more: 1\nend: true"))
            BlocksSpace(template="blocks_v1.yml").managed_content_lock()
            capsys.readouterr()
            BlocksSpace(template="blocks_v2.yml").managed_content_sync()

        assert ci.read_text() == BLOCKS_V2
        assert "editable" not in _lock_entry(project, "ci.yml")
        assert "ci.yml: editable block 'extra' is no longer in the template" in strip_ansi(
            capsys.readouterr().err
        )

    def test_multi_line_block_that_becomes_inline_starts_from_its_default_with_a_note(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture, make_template
    ) -> None:
        ci = project / "ci.yml"
        block = make_template("a:\n{% editable x %}\n  - 1\n{% endeditable %}\n", name="v1.yml")
        inline = make_template("a: {% editable x %}[1]{% endeditable %}\n", name="v2.yml")
        with ctx:
            _template_space("ci.yml", block).managed_content_sync()
            ci.write_text(f"# {HEADER}\na:\n  - 1\n  - 2\n")
            _template_space("ci.yml", block).managed_content_lock()
            capsys.readouterr()
            _template_space("ci.yml", inline).managed_content_sync()

        assert ci.read_text() == f"# {HEADER}\na: [1]\n"
        assert "editable" not in _lock_entry(project, "ci.yml")
        assert "ci.yml: editable block 'x' is now inline, its content is dropped" in strip_ansi(
            capsys.readouterr().err
        )

    def test_one_line_block_that_becomes_inline_keeps_its_content(
        self, ctx: Context, project: Path, make_template
    ) -> None:
        ci = project / "ci.yml"
        block = make_template("a:\n{% editable x %}\n1\n{% endeditable %}\n", name="v1.yml")
        inline = make_template("a: {% editable x %}1{% endeditable %}\n", name="v2.yml")
        with ctx:
            _template_space("ci.yml", block).managed_content_sync()
            ci.write_text(f"# {HEADER}\na:\n2\n")
            _template_space("ci.yml", block).managed_content_lock()
            _template_space("ci.yml", inline).managed_content_sync()

        assert ci.read_text() == f"# {HEADER}\na: 2\n"
        assert _lock_entry(project, "ci.yml")["editable"] == {"x": "2"}

    def test_hand_upgrade_with_unlocked_edit_exits_2_and_force_drops_it(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        ci = project / "ci.yml"
        package = _distribution(FIXTURES)
        with ctx:
            BlocksSpace(template="blocks_v1.yml").managed_content_sync()
            ci.write_text(BLOCKS_V1.replace("1.0", "1.5"))
            before = _snapshot(project)
            capsys.readouterr()
            code = _sync_exit_code(BlocksSpace(template="blocks_v2.yml"))
            after_error = _snapshot(project)
            BlocksSpace(template="blocks_v2.yml").managed_content_sync(force=True)

        assert code == 2
        assert after_error == before
        err = strip_ansi(capsys.readouterr().err)
        assert "expected 'name: fixture-v2', but line 2 is 'name: fixture'" in err
        assert f"reinstall the previous {package} and run `bake mc lock`" in err
        assert "bake mc sync --force" in err
        assert ci.read_text() == BLOCKS_V2

    def test_repo_template_hand_upgrade_hint_names_bakefile_py(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        def space(text: str) -> ManagedSpace:
            class RepoSpace(ManagedSpace):
                def _get_managed_files(self) -> dict[str, ManagedFile]:
                    return {"notes.yml": ManagedFile.from_text(text)}

            return RepoSpace()

        notes = project / "notes.yml"
        with ctx:
            space("a: 1\n").managed_content_sync()
            notes.write_text(notes.read_text().replace("a: 1", "a: 2"))
            capsys.readouterr()
            code = _sync_exit_code(space("b: 1\n"))

        assert code == 2
        assert _lock_entry(project, "notes.yml")["template"] == "repo:notes.yml"
        err = strip_ansi(capsys.readouterr().err)
        assert "If its template in bakefile.py changed since, restore the previous one" in err

    def test_repo_template_block_edit_kept_and_locked_then_steady(
        self, ctx: Context, project: Path
    ) -> None:
        class RepoSpace(ManagedSpace):
            def _get_managed_files(self) -> dict[str, ManagedFile]:
                text = "a: 1\n{% editable local %}\nb: 1\n{% endeditable %}\n"
                return {"notes.yml": ManagedFile.from_text(text)}

        notes = project / "notes.yml"
        with ctx:
            RepoSpace().managed_content_sync()
            notes.write_text(notes.read_text().replace("b: 1", "b: 2"))
            RepoSpace().managed_content_sync()
            after_edit = _snapshot(project)
            RepoSpace().managed_content_sync()

        assert notes.read_text() == f"# {HEADER}\na: 1\nb: 2\n"
        entry = _lock_entry(project, "notes.yml")
        assert entry["template"] == "repo:notes.yml"
        assert entry["editable"] == {"local": "b: 2\n"}
        assert _snapshot(project) == after_edit

    def test_mismatch_skips_editable_content_to_name_the_fixed_line(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        ci = project / "ci.yml"
        with ctx:
            BlocksSpace().managed_content_sync()
            ci.write_text(
                BLOCKS_V1.replace("    - build\n", "    - build\n    - more\n").replace(
                    "end: true", "end: false"
                )
            )
            capsys.readouterr()
            code = _sync_exit_code(BlocksSpace())

        assert code == 2
        assert "expected 'end: true', but line 10 is 'end: false'" in strip_ansi(
            capsys.readouterr().err
        )


class TestRenovateBump:
    def _bump(self, project: Path) -> str:
        bumped = BLOCKS_V1.replace("version: 1.0", "version: 1.1")
        (project / "ci.yml").write_text(bumped)
        return bumped

    def test_setup_dev_keeps_the_bump_and_updates_the_lock(
        self, ctx: Context, project: Path
    ) -> None:
        with ctx:
            BlocksSpace().managed_content_sync()
            bumped = self._bump(project)
            with patch.object(ctx, "run"):
                BlocksSpace().setup_dev(fast=2)

        assert (project / "ci.yml").read_text() == bumped
        assert _lock_entry(project, "ci.yml")["editable"] == {"version": "1.1"}

    def test_lint_keeps_the_bump_and_updates_the_lock(self, ctx: Context, project: Path) -> None:
        with ctx:
            BlocksSpace().managed_content_sync()
            bumped = self._bump(project)
            with patch.object(ctx, "run"):
                BlocksSpace().lint()

        assert (project / "ci.yml").read_text() == bumped
        assert _lock_entry(project, "ci.yml")["editable"] == {"version": "1.1"}


SPACE_LINES = (
    "# Lines from bakefile.py; to change them, override _get_gitignore_lines()\n"
    "**/.ssh/*_id_*\n**/.ssh/id_*\n**/.ssh/known_hosts\n*.local.md\n*.local.toml\n"
    ".claude/settings.local.json\n.claude/worktrees/\n.env*\n.playwright-mcp/\n.scratch\n"
)
REPO_BLOCK = "# (editable)\n"
HAND_GITIGNORE = (
    "# Created by https://www.toptal.com/developers/gitignore/api/python\n"
    "__pycache__/\n\n### repo ###\n/out\n"
)
TEMPLATES_START = "# Created from github/gitignore@"
TEMPLATES_LINE = "# Templates: "


class TestHeaderlessFile:
    def test_hand_gitignore_exits_2_and_force_writes_an_empty_repo_block(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        gitignore = project / ".gitignore"
        gitignore.write_text(HAND_GITIGNORE)
        with ctx:
            code = _sync_exit_code(ManagedSpace())
            after_error = _snapshot(project)
            err = " ".join(strip_ansi(capsys.readouterr().err).split())
            ManagedSpace().managed_content_sync(force=True)

        assert code == 2
        assert after_error == {".gitignore": HAND_GITIGNORE.encode()}
        assert ".gitignore: exists without the managed header" in err
        assert "call `.detach()` on its entry" in err
        text = gitignore.read_text()
        assert text.startswith(f"# {HEADER}\n\n{TEMPLATES_START}")
        assert text.endswith(f"\n\n{SPACE_LINES}\n{REPO_BLOCK}")
        assert "editable" not in _lock_entry(project, ".gitignore")

    def test_line_another_tool_appends_lands_in_the_trailing_block(
        self, ctx: Context, project: Path
    ) -> None:
        gitignore = project / ".gitignore"
        with ctx:
            ManagedSpace().managed_content_sync()
            appended = gitignore.read_text() + "tool-cache/\n"
            gitignore.write_text(appended)
            ManagedSpace().managed_content_sync()

        assert gitignore.read_text() == appended
        assert _lock_entry(project, ".gitignore")["editable"] == {"repo": "tool-cache/\n"}

    def test_headerless_file_exits_2_and_force_writes_defaults(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        ci = project / "ci.yml"
        ci.write_bytes(b"name: mine\n")
        with ctx:
            code = _sync_exit_code(BlocksSpace())
            after_error = _snapshot(project)
            BlocksSpace().managed_content_sync(force=True)

        assert code == 2
        assert after_error == {"ci.yml": b"name: mine\n"}
        assert "ci.yml: exists without the managed header" in strip_ansi(capsys.readouterr().err)
        assert ci.read_text() == BLOCKS_V1


class TestTakeover:
    def test_headerless_file_equal_to_the_defaults_is_taken_over_with_a_note(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture
    ) -> None:
        ci = project / "ci.yml"
        ci.write_text(BLOCKS_V1.removeprefix(f"# {HEADER}\n"))
        with ctx:
            code = _sync_exit_code(BlocksSpace())

        assert code == 0
        assert ci.read_text() == BLOCKS_V1
        assert "ci.yml: taken over, it already equals what bake writes" in strip_ansi(
            capsys.readouterr().err
        )
        assert "editable" not in _lock_entry(project, "ci.yml")

    def test_headerless_markdown_equal_to_the_defaults_leaves_its_editable_block_empty(
        self, ctx: Context, project: Path
    ) -> None:
        class NotesSpace(ManagedSpace):
            def _get_managed_files(self) -> dict[str, ManagedFile]:
                return {"NOTES.md": ManagedFile(FIXTURES, "notes_block.md")}

        notes = project / "NOTES.md"
        with ctx:
            NotesSpace().managed_content_sync()
            written = notes.read_text()
            (project / "bake.lock").unlink()
            notes.write_text(written.removeprefix(f"<!-- {HEADER} -->\n\n"))
            NotesSpace().managed_content_sync()

        assert notes.read_text() == written
        assert "editable" not in _lock_entry(project, "NOTES.md")


class TestFnoxGitignore:
    def test_fnox_append_is_a_no_op_on_the_managed_gitignore(
        self, ctx: Context, project: Path
    ) -> None:
        gitignore = project / ".gitignore"
        with ctx:
            ManagedSpace().managed_content_sync()
            before = gitignore.read_text()
            _ensure_gitignored(project / FNOX_LOCAL_FILE)

        assert gitignore.read_text() == before


class TestRenovateConfig:
    def test_github_actions_tools_writes_renovate_config_keeping_repo_rules(
        self, ctx: Context, project: Path
    ) -> None:
        class GitHubSpace(GitHubActionsTools):
            bake_manage_content: bool = True

        renovate = project / ".github" / "renovate.json5"
        with ctx:
            GitHubSpace().managed_content_sync()
            written = renovate.read_text()
            edited = written.replace(
                "    // (editable)\n",
                "    // (editable)\n    automerge: true,\n",
            )
            renovate.write_text(edited)
            GitHubSpace().managed_content_sync()

        assert written == (
            f"// {HEADER}\n{{\n"
            '    $schema: "https://docs.renovatebot.com/renovate-schema.json",\n'
            '    extends: ["config:recommended"],\n'
            "    // (editable)\n}\n"
        )
        assert renovate.read_text() == edited
        assert _lock_entry(project, ".github/renovate.json5")["editable"] == {
            "rules": "    automerge: true,\n"
        }


RELEASERC = Path(__file__).parents[4] / ".releaserc.mjs"
SEMANTIC_PR_WORKFLOW = (
    Path(__file__).parents[4] / ".github" / "workflows" / "semantic-pull-request.yml"
)
SEMANTIC_PR_PATH = ".github/workflows/semantic-pull-request.yml"


class ManagedZervSpace(ZervGitHubActionsTools):
    bake_manage_content: bool = True


class TestZervGitHubActionsTools:
    def test_writes_releaserc_as_a_whole_fixed_file(self, ctx: Context, project: Path) -> None:
        with ctx:
            ManagedZervSpace().managed_content_sync()

        assert (project / ".releaserc.mjs").read_text() == RELEASERC.read_text()

    def test_writes_semantic_pull_request_workflow_with_editable_steps(
        self, ctx: Context, project: Path
    ) -> None:
        with ctx:
            ManagedZervSpace().managed_content_sync()

        assert (project / SEMANTIC_PR_PATH).read_text() == SEMANTIC_PR_WORKFLOW.read_text()


CI_PATH = ".github/workflows/ci.yml"
CD_PATH = ".github/workflows/cd.yml"
SPACE_JOBS_MARKER = "    # (editable) jobs\n"
TEST_JOB = (
    "    test:\n"
    "        uses: ./.github/workflows/test.yml\n"
    "        secrets:\n"
    "            SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}\n"
)


class ZervPythonLibSpace(ZervGitHubActionsTools, PythonLibSpace):
    bake_manage_content: bool = True


class TestCiCdWorkflows:
    @pytest.mark.parametrize("space", [ManagedZervSpace, ZervPythonLibSpace])
    @pytest.mark.parametrize("path", [CI_PATH, CD_PATH])
    def test_writes_zerv_jobs_and_an_empty_jobs_block(
        self, ctx: Context, project: Path, space: type[BaseSpace], path: str
    ) -> None:
        with ctx:
            space().managed_content_sync()

        written = (project / path).read_text()
        assert "    # (editable) versioning and release\n" in written
        assert "wislertt/zerv/.github/workflows/shared-zerv-versioning.yml@" in written
        assert written.endswith(f"{SPACE_JOBS_MARKER}\n{REPO_JOBS_MARKER}")
        assert "editable" not in _lock_entry(project, path)

    @pytest.mark.parametrize("path", [CI_PATH, CD_PATH])
    def test_jobs_filled_in_by_hand_are_kept(self, ctx: Context, project: Path, path: str) -> None:
        workflow = project / path
        with ctx:
            ManagedZervSpace().managed_content_sync()
            edited = workflow.read_text().replace(SPACE_JOBS_MARKER, SPACE_JOBS_MARKER + TEST_JOB)
            workflow.write_text(edited)
            ManagedZervSpace().managed_content_sync()

        assert workflow.read_text() == edited
        assert _lock_entry(project, path)["editable"] == {"space_jobs": TEST_JOB}

    @pytest.mark.parametrize("path", [CI_PATH, CD_PATH])
    def test_pin_bump_in_the_zerv_jobs_survives_sync(
        self, ctx: Context, project: Path, path: str
    ) -> None:
        workflow = project / path
        with ctx:
            ManagedZervSpace().managed_content_sync()
            bumped = PINNED_SHA.sub("@" + "a" * 40, workflow.read_text())
            workflow.write_text(bumped)
            ManagedZervSpace().managed_content_sync()

        assert workflow.read_text() == bumped
        assert set(_lock_entry(project, path)["editable"]) == {"versioning"}


class ManagedGitHubSpace(GitHubActionsTools):
    bake_manage_content: bool = True


class ManagedPythonSpace(PythonSpace):
    bake_manage_content: bool = True


class ManagedPythonLibSpace(PythonLibSpace):
    bake_manage_content: bool = True


SECURITY_PATH = ".github/workflows/security.yml"
PRE_COMMIT_PATH = ".github/workflows/pre-commit.yml"
PUBLISH_PATH = ".github/workflows/publish.yml"
TEST_PATH = ".github/workflows/test.yml"


class RepoWorkflowsSpace(ManagedPythonLibSpace):
    def _get_managed_files(self) -> dict[str, ManagedFile]:
        return {
            **super()._get_managed_files(),
            TEST_PATH: ManagedFile("bakelib.space", "test.yml"),
            PRE_COMMIT_PATH: ManagedFile("bakelib.space", "pre-commit.yml"),
            PUBLISH_PATH: ManagedFile("bakelib.space", "publish.yml"),
        }


PINNED_SHA = re.compile(r"@[0-9a-f]{40}\b")
REPO_JOBS_MARKER = "    # (editable) more jobs below\n"
WORKFLOWS = [
    pytest.param(ManagedGitHubSpace, SECURITY_PATH, id="security"),
    pytest.param(RepoWorkflowsSpace, PRE_COMMIT_PATH, id="pre-commit"),
    pytest.param(RepoWorkflowsSpace, PUBLISH_PATH, id="publish"),
    pytest.param(RepoWorkflowsSpace, TEST_PATH, id="test"),
]
PINNED_WORKFLOWS = [
    *WORKFLOWS,
    pytest.param(ManagedZervSpace, SEMANTIC_PR_PATH, id="semantic-pull-request"),
]
REPO_STEPS_MARKER = "            # (editable) more steps below\n"
STEPS_WORKFLOWS = [
    pytest.param(RepoWorkflowsSpace, PRE_COMMIT_PATH, "pre_commit_steps", id="pre-commit"),
    pytest.param(RepoWorkflowsSpace, PUBLISH_PATH, "publish_steps", id="publish"),
    pytest.param(
        ManagedZervSpace,
        SEMANTIC_PR_PATH,
        "semantic_pull_request_steps",
        id="semantic-pull-request",
    ),
]


class TestWorkflows:
    def test_security_workflow_scans_with_trivy_and_gitleaks(
        self, ctx: Context, project: Path
    ) -> None:
        with ctx:
            ManagedGitHubSpace().managed_content_sync()

        written = (project / SECURITY_PATH).read_text()
        assert written.startswith(f"# {HEADER}\nname: security\non:\n    # (editable)\n    push:\n")
        assert (
            "    trivy-scan:\n"
            "        runs-on: ubuntu-latest # (editable)\n"
            "        timeout-minutes: 10 # (editable)\n"
            "        steps:\n"
        ) in written
        assert (
            "    gitleaks:\n"
            "        name: gitleaks\n"
            "        runs-on: ubuntu-latest # (editable)\n"
            "        timeout-minutes: 10 # (editable)\n"
            "        steps:\n"
        ) in written
        assert "              # (editable) pin\n              uses: aquasecurity/trivy-action@" in (
            written
        )
        assert "              # (editable) pin\n              uses: gitleaks/gitleaks-action@" in (
            written
        )
        assert (
            "                  # (editable) more trivy-action inputs\n\n    gitleaks:\n" in written
        )
        assert written.endswith(REPO_JOBS_MARKER)
        assert "cargo" not in written

    def test_company_space_inserts_trivy_inputs_and_a_job_at_the_security_hooks(
        self, ctx: Context, project: Path
    ) -> None:
        class CompanySpace(ManagedGitHubSpace):
            def _get_managed_files(self) -> dict[str, ManagedFile]:
                files = super()._get_managed_files()
                files[SECURITY_PATH] = (
                    files[SECURITY_PATH]
                    .insert("trivy_inputs", "severity: HIGH,CRITICAL\n")
                    .insert("extra_jobs", "audit:\n    runs-on: ubuntu-latest\n")
                )
                return files

        workflow = project / SECURITY_PATH
        with ctx:
            CompanySpace().managed_content_sync()
            edited = workflow.read_text().replace(
                "CRITICAL\n", "CRITICAL\n                  ignore-unfixed: true\n"
            )
            workflow.write_text(edited)
            CompanySpace().managed_content_sync()

        assert (
            "                  # (editable) more trivy-action inputs\n"
            "                  severity: HIGH,CRITICAL\n"
            "                  ignore-unfixed: true\n\n"
        ) in workflow.read_text()
        assert workflow.read_text().endswith(
            "    audit:\n        runs-on: ubuntu-latest\n" + REPO_JOBS_MARKER
        )
        assert set(_lock_entry(project, SECURITY_PATH)["editable"]) == {"trivy_with"}

    def test_company_space_inserts_gitleaks_env_and_repo_edits_permissions(
        self, ctx: Context, project: Path
    ) -> None:
        class CompanySpace(ManagedGitHubSpace):
            def _get_managed_files(self) -> dict[str, ManagedFile]:
                files = super()._get_managed_files()
                files[SECURITY_PATH] = files[SECURITY_PATH].insert(
                    "gitleaks_env_vars", "GITLEAKS_LICENSE: ${{ secrets.GITLEAKS_LICENSE }}\n"
                )
                return files

        workflow = project / SECURITY_PATH
        with ctx:
            CompanySpace().managed_content_sync()
            edited = workflow.read_text().replace(
                "    contents: read\n", "    contents: read\n    pull-requests: write\n"
            )
            workflow.write_text(edited)
            CompanySpace().managed_content_sync()

        written = workflow.read_text()
        assert (
            "# (editable)\npermissions:\n    contents: read\n    pull-requests: write\n\n"
            "concurrency:\n"
        ) in written
        assert (
            "                  GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}\n"
            "                  # (editable) more gitleaks-action env\n"
            "                  GITLEAKS_LICENSE: ${{ secrets.GITLEAKS_LICENSE }}\n\n"
        ) in written
        assert set(_lock_entry(project, SECURITY_PATH)["editable"]) == {"permissions"}

    @pytest.mark.parametrize(("space", "path"), PINNED_WORKFLOWS)
    def test_each_pin_and_runs_on_carries_its_editable_note(
        self, ctx: Context, project: Path, space: type[BaseSpace], path: str
    ) -> None:
        with ctx:
            space().managed_content_sync()

        lines = (project / path).read_text().splitlines()
        uses = [i for i, line in enumerate(lines) if PINNED_SHA.search(line)]
        runs_on = [line for line in lines if "runs-on:" in line or "timeout-minutes:" in line]
        assert uses
        assert all(lines[i - 1].strip() == "# (editable) pin" for i in uses)
        assert runs_on
        assert all(line.endswith(" # (editable)") for line in runs_on)

    def test_pre_commit_workflow_skips_the_lint_hook_and_runs_the_slow_lint(
        self, ctx: Context, project: Path
    ) -> None:
        with ctx:
            RepoWorkflowsSpace().managed_content_sync()

        written = (project / PRE_COMMIT_PATH).read_text()
        assert written.startswith(
            f"# {HEADER}\nname: pre-commit\n\non:\n    workflow_call:\n\njobs:\n"
            "    pre-commit:\n        runs-on: ubuntu-latest # (editable)\n"
            "        timeout-minutes: 30 # (editable)\n"
            "        steps:\n"
        )
        assert "              run: SKIP=lint uv run pre-commit run --all-files\n" in written
        assert "              run: bake lint --slow\n" in written
        assert written.endswith(REPO_JOBS_MARKER)

    def test_publish_workflow_runs_bake_publish_with_the_called_version(
        self, ctx: Context, project: Path
    ) -> None:
        with ctx:
            RepoWorkflowsSpace().managed_content_sync()

        written = (project / PUBLISH_PATH).read_text()
        assert written.startswith(
            f"# {HEADER}\nname: publish-python-package\n\non:\n    workflow_call:\n"
        )
        assert (
            "    publish:\n"
            "        runs-on: ubuntu-latest # (editable)\n"
            "        timeout-minutes: 15 # (editable)\n"
            "        steps:\n"
        ) in written
        assert "                  VERSION: ${{ inputs.version }}\n" in written
        assert (
            '              run: bake publish --registry "$REGISTRY" --version "$VERSION"\n'
            in written
        )
        assert not [line for line in written.splitlines() if "run:" in line and "inputs." in line]
        assert written.endswith(REPO_JOBS_MARKER)

    @pytest.mark.parametrize("space", [ManagedPythonSpace, ManagedPythonLibSpace])
    def test_python_spaces_write_no_github_workflow(
        self, ctx: Context, project: Path, space: type[BaseSpace]
    ) -> None:
        with ctx:
            space().managed_content_sync()

        assert not (project / ".github").exists()

    @pytest.mark.parametrize(("space", "path"), PINNED_WORKFLOWS)
    @pytest.mark.parametrize("command", ["managed_content_sync", "lint"])
    def test_pin_bump_in_steps_survives(
        self, ctx: Context, project: Path, space: type[BaseSpace], path: str, command: str
    ) -> None:
        workflow = project / path
        with ctx:
            space().managed_content_sync()
            bumped = PINNED_SHA.sub("@" + "a" * 40, workflow.read_text())
            workflow.write_text(bumped)
            with patch.object(ctx, "run"):
                getattr(space(), command)()

        assert "a" * 40 in bumped
        assert workflow.read_text() == bumped
        assert "a" * 40 in "".join(_lock_entry(project, path)["editable"].values())

    @pytest.mark.parametrize(("space", "path"), WORKFLOWS)
    def test_repo_only_job_after_the_last_marker_is_kept(
        self, ctx: Context, project: Path, space: type[BaseSpace], path: str
    ) -> None:
        job = "    mine:\n        runs-on: ubuntu-latest\n        steps:\n            - run: true\n"
        workflow = project / path
        with ctx:
            space().managed_content_sync()
            workflow.write_text(workflow.read_text() + job)
            space().managed_content_sync()

        assert workflow.read_text().endswith(REPO_JOBS_MARKER + job)
        assert _lock_entry(project, path)["editable"] == {"jobs": job}

    @pytest.mark.parametrize(("space", "path", "block"), STEPS_WORKFLOWS)
    def test_repo_step_after_the_last_step_is_kept_across_sync_and_upgrade(
        self, ctx: Context, project: Path, space: type[BaseSpace], path: str, block: str
    ) -> None:
        base: Any = space

        class UpgradedSpace(base):
            def _get_managed_files(self) -> dict[str, ManagedFile]:
                files = super()._get_managed_files()
                current = files[path]
                # stands in for a release that changes the template's fixed text
                files[path] = ManagedFile.from_text(
                    current.read_template().replace(
                        "        steps:\n", "        timeout-minutes: 30\n        steps:\n", 1
                    ),
                    package=current.package,
                    name=current.name,
                )
                return files

        step = "            - name: mine\n              run: true\n"
        workflow = project / path
        with ctx:
            space().managed_content_sync()
            workflow.write_text(
                workflow.read_text().replace(REPO_STEPS_MARKER, REPO_STEPS_MARKER + step)
            )
            space().managed_content_sync()
            synced = workflow.read_text()
            UpgradedSpace().managed_content_sync()

        upgraded = workflow.read_text()
        assert REPO_STEPS_MARKER + step in synced
        assert "        timeout-minutes: 30\n" in upgraded
        assert REPO_STEPS_MARKER + step in upgraded
        assert _lock_entry(project, path)["editable"] == {block: step}


class ValueSpace(ManagedSpace):
    target: str = "ci.yml"
    template: str = "t.yml"
    project_name: str = "demo"
    jobs: str = ""

    def _get_managed_files(self) -> dict[str, ManagedFile]:
        return {self.target: ManagedFile(TEMPLATE_PACKAGE, self.template)}

    @override
    def _get_managed_values(self, fetch: Fetch) -> dict[str, str]:
        return {"project_name": self.project_name, "extra_jobs": self.jobs}


VALUE_TEMPLATE = """name: {{ bakefile.project_name }}
jobs:
    build: {}
    # jobs from Spaces
    {{ bakefile.extra_jobs }}
    # end of jobs from Spaces
"""


class TestBakefileValues:
    def test_setting_and_hook_values_are_rendered_and_never_locked(
        self, ctx: Context, project: Path, make_template
    ) -> None:
        make_template(VALUE_TEMPLATE)
        with ctx:
            ValueSpace(jobs="test:\n    needs: build\n").managed_content_sync()

        assert (project / "ci.yml").read_text() == (
            f"# {HEADER}\nname: demo\njobs:\n    build: {{}}\n    # jobs from Spaces\n"
            "    test:\n        needs: build\n    # end of jobs from Spaces\n"
        )
        assert set(_lock_entry(project, "ci.yml")) == {"template", "hash"}

    def test_block_and_value_names_are_read_from_the_template_text(
        self, ctx: Context, project: Path, make_template
    ) -> None:
        make_template(
            "name: {{ bakefile.project_name }}\n# (editable) more\n"
            "{% editable more %}\n{% endeditable %}\n"
        )
        ci = project / "ci.yml"
        with ctx:
            ValueSpace().managed_content_sync()
            ci.write_text(ci.read_text() + "mine: 1\n")
            ValueSpace().managed_content_sync()

        assert ci.read_text() == f"# {HEADER}\nname: demo\n# (editable) more\nmine: 1\n"
        assert _lock_entry(project, "ci.yml")["editable"] == {"more": "mine: 1\n"}

    def test_changed_hook_value_is_rewritten_with_a_note_keeping_editable_blocks(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture, make_template
    ) -> None:
        make_template(
            VALUE_TEMPLATE + "# (editable) more\n{% editable more %}\n{% endeditable %}\n"
        )
        ci = project / "ci.yml"

        with ctx:
            ValueSpace(jobs="lint: {}\n").managed_content_sync()
            ci.write_text(ci.read_text() + "mine: 1\n")
            capsys.readouterr()
            ValueSpace(jobs="lint: {}\ntest: {}\n").managed_content_sync()

        assert ci.read_text().endswith(
            "    lint: {}\n    test: {}\n    # end of jobs from Spaces\n"
            "# (editable) more\nmine: 1\n"
        )
        err = strip_ansi(capsys.readouterr().err)
        assert "ci.yml: bakefile value 'extra_jobs' differs from what the Bakebook gives now" in err

    def test_hand_edit_inside_a_value_is_reverted_with_a_note_and_lint_reports_drift(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture, make_template
    ) -> None:
        make_template(VALUE_TEMPLATE)
        ci = project / "ci.yml"
        with ctx:
            ValueSpace(jobs="lint: {}\n").managed_content_sync()
            written = ci.read_text()
            ci.write_text(written.replace("name: demo", "name: mine"))
            with patch.object(ctx, "run"), pytest.raises(typer.Exit) as exc_info:
                ValueSpace(jobs="lint: {}\n").lint()
            capsys.readouterr()
            ValueSpace(jobs="lint: {}\n").managed_content_sync()

        assert exc_info.value.exit_code == 1
        assert ci.read_text() == written
        assert "bakefile value 'project_name' differs" in strip_ansi(capsys.readouterr().err)

    def test_removed_hook_value_empties_it_and_its_banner_stays(
        self, ctx: Context, project: Path, make_template
    ) -> None:
        make_template(VALUE_TEMPLATE)
        with ctx:
            ValueSpace(jobs="lint: {}\n").managed_content_sync()
            ValueSpace().managed_content_sync()

        assert (project / "ci.yml").read_text() == (
            f"# {HEADER}\nname: demo\njobs:\n    build: {{}}\n    # jobs from Spaces\n"
            "    # end of jobs from Spaces\n"
        )

    def test_multi_line_value_is_indented_without_trailing_whitespace(
        self, ctx: Context, project: Path, make_template
    ) -> None:
        make_template(VALUE_TEMPLATE)
        with ctx:
            ValueSpace(jobs="a: 1\n\nb:\n    c: 2").managed_content_sync()

        assert (
            "    # jobs from Spaces\n    a: 1\n\n    b:\n        c: 2\n    # end"
            in (project / "ci.yml").read_text()
        )

    def test_default_may_contain_a_value_and_follows_it_while_untouched(
        self, ctx: Context, project: Path, make_template
    ) -> None:
        name = make_template(
            "name: {% editable name %}{{ bakefile.project_name }}-ci{% endeditable %}\n"
        )

        class Space(ManagedSpace):
            project_name: str = "demo"

            def _get_managed_files(self) -> dict[str, ManagedFile]:
                return {"ci.yml": ManagedFile(TEMPLATE_PACKAGE, name)}

            @override
            def _get_managed_values(self, fetch: Fetch) -> dict[str, str]:
                return {"project_name": self.project_name}

        with ctx:
            Space().managed_content_sync()
            first = (project / "ci.yml").read_text()
            Space(project_name="other").managed_content_sync()

        assert first == f"# {HEADER}\nname: demo-ci\n"
        assert (project / "ci.yml").read_text() == f"# {HEADER}\nname: other-ci\n"

    def test_raw_passes_tag_like_text_through(
        self, ctx: Context, project: Path, make_template
    ) -> None:
        name = make_template(
            "a: {% raw %}{{ bakefile.x }} {% editable y %}{% endraw %}\n"
            "b: {% raw %}{%{% endraw %}\n"
            "c: {% editable c %}{% raw %}{%{% endraw %}{% endeditable %}\n"
        )
        with ctx:
            _template_space("ci.yml", name).managed_content_sync()
            _template_space("ci.yml", name).managed_content_sync()

        assert (project / "ci.yml").read_text() == (
            f"# {HEADER}\na: {{{{ bakefile.x }}}} {{% editable y %}}\nb: {{%\nc: {{%\n"
        )
        assert "editable" not in _lock_entry(project, "ci.yml")

    @pytest.mark.parametrize(
        ("template", "message"),
        [
            pytest.param(
                "a:\n{% editable x %}\n{% endeditable %}\n{{ bakefile.extra_jobs }}\n"
                "{{ bakefile.project_name }}\n",
                "bakefile value 'extra_jobs' needs fixed text between it "
                "and the editable block 'x'",
                id="adjacent",
            ),
            pytest.param(
                "a: {{ bakefile.extra_jobs }}\n# {{ bakefile.project_name }}\n",
                "bakefile value 'extra_jobs' has more than one line, so its tag must sit alone",
                id="multi-line-inline",
            ),
            pytest.param(
                "a: {{bakefile.extra_jobs}}\n",
                "malformed tag near '{{bakefile.extra_jobs",
                id="near-miss",
            ),
            pytest.param(
                "a: {% raw %}{{ bakefile.extra_jobs }}\n",
                "`{% raw %}` needs `{% endraw %}`",
                id="unclosed-raw",
            ),
        ],
    )
    def test_load_error_exits_2_and_writes_nothing(
        self,
        ctx: Context,
        project: Path,
        capsys: pytest.CaptureFixture,
        make_template,
        template: str,
        message: str,
    ) -> None:
        make_template(template)

        with ctx:
            code = _sync_exit_code(ValueSpace(jobs="a\nb\n"))

        assert code == 2
        assert message in strip_ansi(capsys.readouterr().err)
        assert list(project.iterdir()) == []

    def test_value_that_is_not_text_exits_2(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture, make_template
    ) -> None:
        name = make_template("a: {{ bakefile.count }}\n")

        class Space(ManagedSpace):
            count: Any = 3

            def _get_managed_files(self) -> dict[str, ManagedFile]:
                return {"ci.yml": ManagedFile(TEMPLATE_PACKAGE, name)}

            @override
            def _get_managed_values(self, fetch: Fetch) -> dict[str, Any]:
                return {"count": self.count}

        with ctx:
            code = _sync_exit_code(Space())

        assert code == 2
        assert "bakefile value 'count' must be text, got int" in strip_ansi(capsys.readouterr().err)
        assert list(project.iterdir()) == []


class TestManagedValues:
    def test_value_the_bakebook_does_not_give_exits_2(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture, make_template
    ) -> None:
        name = make_template("a: {{ bakefile.missing }}\n")

        class Space(ManagedSpace):
            def _get_managed_files(self) -> dict[str, ManagedFile]:
                return {"ci.yml": ManagedFile(TEMPLATE_PACKAGE, name)}

        with ctx:
            code = _sync_exit_code(Space())

        assert code == 2
        assert "bakefile value 'missing' is not among the values the Bakebook gives" in strip_ansi(
            capsys.readouterr().err
        )
        assert list(project.iterdir()) == []

    @pytest.mark.usefixtures("project")
    def test_only_sync_may_fetch_and_only_refresh_fetches_again(
        self, ctx: Context, make_template
    ) -> None:
        make_template("pin: {{ bakefile.pin }}\n")
        modes: list[Fetch] = []

        class PinSpace(ManagedSpace):
            def _get_managed_files(self) -> dict[str, ManagedFile]:
                return {"ci.yml": ManagedFile(TEMPLATE_PACKAGE, "t.yml")}

            def _get_managed_values(self, fetch: Fetch) -> dict[str, str]:
                modes.append(fetch)
                return {"pin": "1"}

        with ctx:
            PinSpace().managed_content_sync()
            sync_modes = list(modes)
            modes.clear()
            PinSpace().managed_content_sync(refresh=True)
            refresh_modes = list(modes)
            modes.clear()
            PinSpace().managed_content_lock()
            _lint_exit_code(PinSpace(), ctx)

        assert sync_modes == [Fetch.WHEN_NEEDED]
        assert refresh_modes == [Fetch.REFRESH]
        assert set(modes) == {Fetch.NEVER}

    @pytest.mark.usefixtures("project")
    def test_lint_builds_the_values_once_for_its_lock_and_check(
        self, ctx: Context, make_template
    ) -> None:
        make_template("pin: {{ bakefile.pin }}\n")
        modes: list[Fetch] = []

        class PinSpace(ManagedSpace):
            def _get_managed_files(self) -> dict[str, ManagedFile]:
                return {"ci.yml": ManagedFile(TEMPLATE_PACKAGE, "t.yml")}

            def _get_managed_values(self, fetch: Fetch) -> dict[str, str]:
                modes.append(fetch)
                return {"pin": "1"}

        with ctx:
            _lint_exit_code(PinSpace(), ctx)

        assert modes == [Fetch.NEVER]


class NodeSpace(ManagedSpace):
    def _get_gitignore_lines(self) -> set[str]:
        return super()._get_gitignore_lines() | {"node_modules/"}


class TestGitignoreLines:
    def test_child_space_line_is_sorted_in_and_the_repo_block_is_kept(
        self, ctx: Context, project: Path
    ) -> None:
        gitignore = project / ".gitignore"
        with ctx:
            NodeSpace().managed_content_sync()
            edited = gitignore.read_text() + "/repo-rule\n"
            gitignore.write_text(edited)
            NodeSpace().managed_content_sync()

        assert edited.startswith(f"# {HEADER}\n\n{TEMPLATES_START}")
        assert edited.endswith(f"{SPACE_LINES}node_modules/\n\n{REPO_BLOCK}/repo-rule\n")
        assert gitignore.read_text() == edited

    def test_child_space_removes_a_parent_line_and_its_negation_comes_last(
        self, ctx: Context, project: Path
    ) -> None:
        class NegatingSpace(ManagedSpace):
            def _get_gitignore_lines(self) -> set[str]:
                return (super()._get_gitignore_lines() - {".scratch"}) | {"!.env.example"}

        with ctx:
            NegatingSpace().managed_content_sync()

        without_scratch = SPACE_LINES.removesuffix(".scratch\n")
        text = (project / ".gitignore").read_text()
        assert text.endswith(f"{without_scratch}!.env.example\n\n{REPO_BLOCK}")


SHA_1 = "1" * 40
SHA_2 = "2" * 40
# taken at import, before the autouse fixture swaps in the offline stand-in
_DEFAULT_GITIGNORE_UPSTREAM = BaseSpace._get_gitignore_upstream


class FakeGitHub:
    def __init__(self) -> None:
        self.sha = SHA_1
        self.calls: list[str] = []
        self.offline = False

    def latest_sha(self) -> str:
        self.calls.append("ls-remote")
        if self.offline:
            raise ManagedContentError("could not read the latest commit: offline")
        return self.sha

    def template(self, sha: str, path: str) -> str:
        self.calls.append(f"{path}@{sha[0]}")
        if path == "Cobol":
            raise TemplateNotFoundError(f"gitignore template {path!r} is not in github/gitignore")
        return f"# {path} at {sha[0]}\n/{path.lower()}-out/\n"


@pytest.fixture
def github(monkeypatch: pytest.MonkeyPatch) -> FakeGitHub:
    fake = FakeGitHub()
    upstream = Upstream(latest_sha=fake.latest_sha, template=fake.template)
    monkeypatch.setattr(BaseSpace, "_get_gitignore_upstream", lambda _self: upstream)
    return fake


class AddTemplateSpace(ManagedSpace):
    def _get_gitignore_templates(self) -> set[str]:
        return super()._get_gitignore_templates() | {"Python"}


class RemoveTemplateSpace(ManagedSpace):
    def _get_gitignore_templates(self) -> set[str]:
        return super()._get_gitignore_templates() - {"Global/Windows"}


class UnknownTemplateSpace(ManagedSpace):
    def _get_gitignore_templates(self) -> set[str]:
        return super()._get_gitignore_templates() | {"Cobol"}


def _template_paths(text: str) -> list[str]:
    return [line.strip("# ") for line in text.splitlines() if line.startswith("### ")]


class DetachedGitignoreSpace(ManagedSpace):
    def _get_managed_files(self) -> dict[str, ManagedFile]:
        files = super()._get_managed_files()
        files[".gitignore"] = files[".gitignore"].detach()
        return files


class TestDetachedGitignore:
    @pytest.mark.parametrize("refresh", [False, True], ids=["sync", "refresh"])
    def test_is_not_fetched_for(
        self, ctx: Context, project: Path, github: FakeGitHub, refresh: bool
    ) -> None:
        gitignore = project / ".gitignore"
        gitignore.write_text(f"# {HEADER}\n# my own section\n")
        github.offline = True
        with ctx:
            DetachedGitignoreSpace().managed_content_sync(refresh=refresh)

        assert github.calls == []
        assert gitignore.read_text() == f"# {HEADER}\n# my own section\n"


class TestGitignoreTemplates:
    def test_templates_come_from_github_gitignore_by_default(
        self, ctx: Context, project: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(BaseSpace, "_get_gitignore_upstream", _DEFAULT_GITIGNORE_UPSTREAM)
        listed = subprocess.CompletedProcess([], 0, stdout=f"{SHA_1}\trefs/heads/main\n")
        urls: list[str] = []

        def urlopen(url: str, **_kwargs: object) -> MagicMock:
            urls.append(url)
            response = MagicMock()
            response.__enter__.return_value.read.return_value = b"/from-github/\n"
            return response

        with (
            patch("subprocess.run", return_value=listed),
            patch("urllib.request.urlopen", side_effect=urlopen),
            ctx,
        ):
            ManagedSpace().managed_content_sync()

        raw = f"https://raw.githubusercontent.com/github/gitignore/{SHA_1}/Global"
        assert sorted(urls) == [
            f"{raw}/VisualStudioCode.gitignore",
            f"{raw}/Windows.gitignore",
            f"{raw}/macOS.gitignore",
        ]
        text = (project / ".gitignore").read_text()
        assert f"{TEMPLATES_START}{SHA_1}\n" in text
        assert "### Global/macOS ###\n/from-github/\n" in text

    def test_first_sync_fetches_the_templates_from_main_sorted_before_the_space_lines(
        self, ctx: Context, project: Path, github: FakeGitHub
    ) -> None:
        with ctx:
            ManagedSpace().managed_content_sync()

        assert (
            (project / ".gitignore")
            .read_text()
            .startswith(
                f"# {HEADER}\n\n"
                f"{TEMPLATES_START}{SHA_1}\n"
                f"{TEMPLATES_LINE}Global/VisualStudioCode, Global/Windows, Global/macOS\n"
                "# To change the templates, override _get_gitignore_templates() in bakefile.py\n"
                "\n### Global/VisualStudioCode ###\n# Global/VisualStudioCode at 1\n"
                "/global/visualstudiocode-out/\n"
                "\n### Global/Windows ###\n# Global/Windows at 1\n/global/windows-out/\n"
                "\n### Global/macOS ###\n# Global/macOS at 1\n/global/macos-out/\n"
                "\n# End of github/gitignore section, sha256:"
            )
        )
        assert (
            "section, sha256:"
            in (project / ".gitignore").read_text().split("# Lines from bakefile.py")[0]
        )
        assert github.calls == [
            "ls-remote",
            "Global/VisualStudioCode@1",
            "Global/Windows@1",
            "Global/macOS@1",
        ]

    def test_same_templates_never_fetch_again_from_sync_setup_dev_or_lint(
        self, ctx: Context, project: Path, github: FakeGitHub
    ) -> None:
        with ctx:
            ManagedSpace().managed_content_sync()
            written = _snapshot(project)
            github.calls.clear()
            github.sha = SHA_2
            ManagedSpace().managed_content_sync()
            with patch.object(ctx, "run"):
                ManagedSpace().setup_dev(fast=2)
            lint_code = _lint_exit_code(ManagedSpace(), ctx)

        assert github.calls == []
        assert lint_code == 0
        assert _snapshot(project) == written

    @pytest.mark.parametrize(
        ("space", "paths", "fetched"),
        [
            pytest.param(
                AddTemplateSpace,
                ["Global/VisualStudioCode", "Global/Windows", "Global/macOS", "Python"],
                ["Global/VisualStudioCode@1", "Global/Windows@1", "Global/macOS@1", "Python@1"],
                id="add",
            ),
            pytest.param(
                RemoveTemplateSpace,
                ["Global/VisualStudioCode", "Global/macOS"],
                ["Global/VisualStudioCode@1", "Global/macOS@1"],
                id="remove",
            ),
        ],
    )
    def test_changed_list_fetches_at_the_section_commit_keeping_editable_blocks(
        self,
        ctx: Context,
        project: Path,
        capsys: pytest.CaptureFixture,
        github: FakeGitHub,
        space: type[ManagedSpace],
        paths: list[str],
        fetched: list[str],
    ) -> None:
        gitignore = project / ".gitignore"
        with ctx:
            ManagedSpace().managed_content_sync()
            gitignore.write_text(gitignore.read_text() + "/repo-rule\n")
            github.calls.clear()
            github.sha = SHA_2
            space().managed_content_sync()
            capsys.readouterr()
            lint_code = _lint_exit_code(space(), ctx)

        text = gitignore.read_text()
        assert github.calls == fetched
        assert f"{TEMPLATES_START}{SHA_1}\n{TEMPLATES_LINE}{', '.join(paths)}\n" in text
        assert _template_paths(text) == paths
        assert text.endswith(f"{REPO_BLOCK}/repo-rule\n")
        assert lint_code == 0
        assert "managed content up to date" in strip_ansi(capsys.readouterr().err)

    def test_lint_reports_a_changed_list_as_drift_without_fetching(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture, github: FakeGitHub
    ) -> None:
        with ctx:
            ManagedSpace().managed_content_sync()
            written = _snapshot(project)
            github.calls.clear()
            lint_code = _lint_exit_code(AddTemplateSpace(), ctx)

        assert lint_code == 1
        assert github.calls == []
        assert _snapshot(project) == written
        err = strip_ansi(capsys.readouterr().err)
        assert ".gitignore: drift" in err
        assert "run `bake mc sync`" in err

    def test_hand_edit_in_the_section_is_drift_and_sync_restores_it_at_its_commit(
        self, ctx: Context, project: Path, capsys: pytest.CaptureFixture, github: FakeGitHub
    ) -> None:
        gitignore = project / ".gitignore"
        with ctx:
            ManagedSpace().managed_content_sync()
            written = gitignore.read_text()
            gitignore.write_text(written.replace("/global/windows-out/\n", "/mine/\n"))
            github.calls.clear()
            github.sha = SHA_2
            lint_code = _lint_exit_code(ManagedSpace(), ctx)
            lint_calls = list(github.calls)
            capsys.readouterr()
            ManagedSpace().managed_content_sync()

        assert lint_code == 1
        assert lint_calls == []
        assert "ls-remote" not in github.calls
        assert gitignore.read_text() == written
        assert "hand edits inside it are not kept" in " ".join(
            strip_ansi(capsys.readouterr().err).split()
        )

    @pytest.mark.parametrize(
        ("space", "old", "new", "commit"),
        [
            pytest.param(
                AddTemplateSpace,
                f"{TEMPLATES_LINE}Global/VisualStudioCode, Global/Windows, Global/macOS\n",
                f"{TEMPLATES_LINE}Global/VisualStudioCode, Global/Windows, Global/macOS, Python\n",
                "1",
                id="templates-line",
            ),
            pytest.param(
                ManagedSpace,
                f"{TEMPLATES_START}{SHA_1}\n",
                f"{TEMPLATES_START}{SHA_2}\n",
                "2",
                id="commit-line",
            ),
        ],
    )
    def test_hand_edit_of_a_start_line_is_drift_and_sync_fetches_at_the_named_commit(
        self,
        ctx: Context,
        project: Path,
        github: FakeGitHub,
        space: type[ManagedSpace],
        old: str,
        new: str,
        commit: str,
    ) -> None:
        gitignore = project / ".gitignore"
        with ctx:
            ManagedSpace().managed_content_sync()
            written = gitignore.read_text()
            gitignore.write_text(written.replace(old, new))
            github.calls.clear()
            lint_code = _lint_exit_code(space(), ctx)
            lint_calls = list(github.calls)
            space().managed_content_sync()
            lint_code_after_sync = _lint_exit_code(space(), ctx)

        templates = sorted(space()._get_gitignore_templates())
        assert written.count(old) == 1
        assert lint_code == 1
        assert lint_calls == []
        assert github.calls == [f"{path}@{commit}" for path in templates]
        assert _template_paths(gitignore.read_text()) == templates
        assert lint_code_after_sync == 0

    @pytest.mark.parametrize(
        ("old", "new"),
        [
            pytest.param(TEMPLATES_LINE, "# Templatez: ", id="templates-line"),
            pytest.param("# End of github/gitignore section", "# End", id="end-line"),
        ],
    )
    def test_hand_edit_that_breaks_the_section_is_restored_at_its_commit(
        self, ctx: Context, project: Path, github: FakeGitHub, old: str, new: str
    ) -> None:
        gitignore = project / ".gitignore"
        with ctx:
            ManagedSpace().managed_content_sync()
            written = gitignore.read_text()
            gitignore.write_text(written.replace(old, new))
            github.calls.clear()
            github.sha = SHA_2
            ManagedSpace().managed_content_sync()

        assert written.count(old) == 1
        assert github.calls == ["Global/VisualStudioCode@1", "Global/Windows@1", "Global/macOS@1"]
        assert gitignore.read_text() == written

    def test_hand_edit_that_breaks_the_commit_line_fetches_from_main(
        self, ctx: Context, project: Path, github: FakeGitHub
    ) -> None:
        gitignore = project / ".gitignore"
        with ctx:
            ManagedSpace().managed_content_sync()
            written = gitignore.read_text()
            gitignore.write_text(written.replace(f"{TEMPLATES_START}{SHA_1}", TEMPLATES_START))
            github.calls.clear()
            github.sha = SHA_2
            ManagedSpace().managed_content_sync()

        text = gitignore.read_text()
        assert github.calls[0] == "ls-remote"
        assert f"{TEMPLATES_START}{SHA_2}\n" in text
        assert TEMPLATES_START + "\n" not in text

    def test_section_pasted_into_the_editable_block_is_not_the_cache(
        self, ctx: Context, project: Path, github: FakeGitHub
    ) -> None:
        gitignore = project / ".gitignore"
        with ctx:
            ManagedSpace().managed_content_sync()
            written = gitignore.read_text()
            section = read_section(written)
            assert section is not None
            gitignore.write_text(written.replace(section.text, "") + section.text)
            github.calls.clear()
            github.sha = SHA_2
            lint_code = _lint_exit_code(ManagedSpace(), ctx)
            lint_calls = list(github.calls)
            ManagedSpace().managed_content_sync()

        text = gitignore.read_text()
        assert lint_code == 1
        assert lint_calls == []
        assert github.calls[0] == "ls-remote"
        assert text.startswith(f"# {HEADER}\n\n{TEMPLATES_START}{SHA_2}\n")
        assert text.endswith(f"{REPO_BLOCK}{section.text}")

    def test_section_in_a_headerless_hand_file_is_not_the_cache(
        self, ctx: Context, project: Path, github: FakeGitHub
    ) -> None:
        gitignore = project / ".gitignore"
        with ctx:
            ManagedSpace().managed_content_sync()
            section = read_section(gitignore.read_text())
            assert section is not None
            (project / "bake.lock").unlink()
            gitignore.write_text(section.text)
            github.calls.clear()
            github.sha = SHA_2
            ManagedSpace().managed_content_sync(force=True)

        text = gitignore.read_text()
        assert github.calls[0] == "ls-remote"
        assert text.startswith(f"# {HEADER}\n\n{TEMPLATES_START}{SHA_2}\n")
        assert text.endswith(f"\n\n{SPACE_LINES}\n{REPO_BLOCK}")

    def test_template_missing_at_the_section_commit_says_to_refresh(
        self, ctx: Context, capsys: pytest.CaptureFixture, github: FakeGitHub
    ) -> None:
        hint = "run `bake mc sync --refresh`"
        with ctx:
            first_code = _sync_exit_code(UnknownTemplateSpace())
            first_err = " ".join(strip_ansi(capsys.readouterr().err).split())
            ManagedSpace().managed_content_sync()
            capsys.readouterr()
            github.calls.clear()
            code = _sync_exit_code(UnknownTemplateSpace())
            kept_calls = list(github.calls)
            err = " ".join(strip_ansi(capsys.readouterr().err).split())
            refresh_code = _sync_exit_code(UnknownTemplateSpace(), refresh=True)
            refresh_err = " ".join(strip_ansi(capsys.readouterr().err).split())

        assert (first_code, code, refresh_code) == (2, 2, 2)
        assert kept_calls == ["Cobol@1"]
        assert "gitignore template 'Cobol' is not in github/gitignore" in err
        assert f"it may have been added after commit {SHA_1}; {hint}" in err
        assert hint not in first_err
        assert hint not in refresh_err

    def test_refresh_fetches_main_again_and_moves_the_commit(
        self, ctx: Context, project: Path, github: FakeGitHub
    ) -> None:
        gitignore = project / ".gitignore"
        with ctx:
            ManagedSpace().managed_content_sync()
            github.sha = SHA_2
            ManagedSpace().managed_content_sync(refresh=True)

        text = gitignore.read_text()
        assert f"{TEMPLATES_START}{SHA_2}\n" in text
        assert "# Global/macOS at 2\n" in text
        assert SHA_1 not in text

    def test_refresh_note_names_the_value_that_changed(
        self, ctx: Context, capsys: pytest.CaptureFixture, github: FakeGitHub
    ) -> None:
        with ctx:
            ManagedSpace().managed_content_sync()
            github.sha = SHA_2
            capsys.readouterr()
            ManagedSpace().managed_content_sync(refresh=True)

        err = " ".join(strip_ansi(capsys.readouterr().err).split())
        assert "bakefile value 'gitignore_stack_section' differs" in err

    @pytest.mark.parametrize(
        ("space", "offline", "message"),
        [
            pytest.param(
                UnknownTemplateSpace,
                False,
                "gitignore template 'Cobol' is not in github/gitignore",
                id="unknown-template",
            ),
            pytest.param(
                ManagedSpace, True, "could not read the latest commit: offline", id="offline"
            ),
        ],
    )
    def test_failed_fetch_exits_2_and_writes_nothing(
        self,
        ctx: Context,
        project: Path,
        capsys: pytest.CaptureFixture,
        github: FakeGitHub,
        space: type[ManagedSpace],
        offline: bool,
        message: str,
    ) -> None:
        (project / ".gitignore").write_bytes(b"/hand\n")
        github.offline = offline
        with ctx:
            code = _sync_exit_code(space())

        assert code == 2
        assert message in " ".join(strip_ansi(capsys.readouterr().err).split())
        assert _snapshot(project) == {".gitignore": b"/hand\n"}

    def test_composition_order_does_not_change_the_file(
        self, ctx: Context, project: Path, github: FakeGitHub
    ) -> None:
        class ListOrderSpace(ManagedSpace):
            def _get_gitignore_templates(self) -> set[str]:
                return {"Python"} | super()._get_gitignore_templates() | {"Python"}

        with ctx:
            AddTemplateSpace().managed_content_sync()
            written = _snapshot(project)
            github.calls.clear()
            ListOrderSpace().managed_content_sync()

        assert github.calls == []
        assert _snapshot(project) == written

    def test_space_without_templates_writes_no_section_and_never_fetches(
        self, ctx: Context, project: Path, github: FakeGitHub
    ) -> None:
        class NoTemplateSpace(ManagedSpace):
            def _get_gitignore_templates(self) -> set[str]:
                return set()

        gitignore = project / ".gitignore"
        with ctx:
            NoTemplateSpace().managed_content_sync()
            NoTemplateSpace().managed_content_sync(refresh=True)
            lint_code = _lint_exit_code(NoTemplateSpace(), ctx)

        assert github.calls == []
        assert lint_code == 0
        assert gitignore.read_text() == f"# {HEADER}\n\n\n{SPACE_LINES}\n{REPO_BLOCK}"

    @pytest.mark.parametrize(
        ("space", "templates"),
        [
            pytest.param(
                BaseSpace, {"Global/macOS", "Global/Windows", "Global/VisualStudioCode"}, id="base"
            ),
            pytest.param(
                PythonSpace,
                {"Global/macOS", "Global/Windows", "Global/VisualStudioCode", "Python"},
                id="python",
            ),
            pytest.param(
                RustSpace,
                {"Global/macOS", "Global/Windows", "Global/VisualStudioCode", "Rust"},
                id="rust",
            ),
        ],
    )
    def test_space_default_templates(self, space: type[BaseSpace], templates: set[str]) -> None:
        assert space.__new__(space)._get_gitignore_templates() == templates

    def test_rust_space_adds_the_rust_analyzer_project_file(self) -> None:
        rust = RustSpace.__new__(RustSpace)._get_gitignore_lines()
        assert rust - BaseSpace.__new__(BaseSpace)._get_gitignore_lines() == {"rust-project.json"}


class TestUpdate:
    def test_renovate_bump_is_locked_before_upgrades_and_post_update_runs_last_as_a_subprocess(
        self, ctx: Context, project: Path
    ) -> None:
        commands: list[str] = []
        locked_before_first_command: list[dict] = []

        def run(cmd: str, *_, **__) -> None:
            if not commands:
                locked_before_first_command.append(_lock_entry(project, "ci.yml"))
            commands.append(cmd)

        ci = project / "ci.yml"
        with ctx:
            BlocksSpace().managed_content_sync()
            bumped = BLOCKS_V1.replace("version: 1.0", "version: 1.1")
            ci.write_text(bumped)
            with patch.object(ctx, "run", side_effect=run):
                BlocksSpace().update(fast=2)

        assert ci.read_text() == bumped
        assert locked_before_first_command[0]["editable"] == {"version": "1.1"}
        assert commands[0] == "pre-commit autoupdate"
        assert commands[-1] == f"bake --chdir {shlex.quote(str(project))} post-update"

    def test_post_update_syncs_with_refresh(
        self, ctx: Context, project: Path, github: FakeGitHub
    ) -> None:
        with ctx:
            ManagedSpace().managed_content_sync()
            github.sha = SHA_2
            ManagedSpace().post_update()

        assert f"{TEMPLATES_START}{SHA_2}\n" in (project / ".gitignore").read_text()
