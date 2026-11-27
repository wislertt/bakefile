from collections.abc import Generator
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from bake import Context
from bake.ui.logger import strip_ansi
from bake.utils.settings import bake_settings
from bakelib import Migration
from bakelib.space.base import BaseSpace


class UnuseToolMigration(Migration):
    expires = date(2099, 1, 1)
    description = "Remove old-tool from mise.toml"

    def __init__(self, *, applies: bool) -> None:
        self.applies = applies

    def check(self, ctx: Context) -> bool:
        _ = ctx
        return self.applies

    def apply(self, ctx: Context) -> None:
        ctx.run("mise unuse old-tool")


class DeleteFileMigration(Migration):
    expires = date(2099, 1, 1)
    description = "Delete old.cfg"

    def __init__(self, path: Path) -> None:
        self.path = path

    def check(self, ctx: Context) -> bool:
        _ = ctx
        return self.path.exists()

    def apply(self, ctx: Context) -> None:
        if ctx.dry_run:
            return
        self.path.unlink()


def space_with(migrations: dict[str, Migration]) -> BaseSpace:
    class MigratingSpace(BaseSpace):
        def _get_migrations(self) -> dict[str, Migration]:
            return {**super()._get_migrations(), **migrations}

    return MigratingSpace()


class ParentSpace(BaseSpace):
    def _get_migrations(self) -> dict[str, Migration]:
        return {**super()._get_migrations(), "unuse-old-tool": UnuseToolMigration(applies=True)}


def _err(capsys: pytest.CaptureFixture) -> str:
    return strip_ansi(capsys.readouterr().err)


@contextmanager
def _setup_steps_stubbed(space: BaseSpace) -> Generator[None]:
    with (
        patch.object(bake_settings, "platform", "macos"),
        patch.object(type(space), "_setup_platform_tools"),
        patch.object(type(space), "_setup_tools"),
        patch.object(type(space), "_setup_project"),
    ):
        yield


class FailingMigration(Migration):
    expires = date(2099, 1, 1)
    description = "Fail on purpose"

    def check(self, ctx: Context) -> bool:
        _ = ctx
        return True

    def apply(self, ctx: Context) -> None:
        _ = ctx
        raise RuntimeError("boom")


class TestLintMigrations:
    @pytest.mark.parametrize("dry_run", [True, False])
    def test_lint_fails_listing_each_applying_migration(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture, dry_run: bool
    ) -> None:
        mock_ctx.dry_run = dry_run
        space = space_with(
            {
                "unuse-old-tool": UnuseToolMigration(applies=True),
                "unuse-other-tool": UnuseToolMigration(applies=False),
            }
        )

        with mock_ctx, pytest.raises(typer.Exit) as exc_info:
            space.lint()

        assert exc_info.value.exit_code == 1
        err = _err(capsys)
        assert "unuse-old-tool" in err
        assert "Remove old-tool from mise.toml" in err
        assert "unuse-other-tool" not in err
        assert "bake setup-dev" in err
        assert "mise unuse" not in err

    def test_lint_passes_when_no_migration_applies(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        space = space_with({"unuse-old-tool": UnuseToolMigration(applies=False)})

        with mock_ctx:
            space.lint()

        err = _err(capsys)
        assert "unuse-old-tool" not in err
        assert "oxfmt" in err

    def test_lint_ignores_migration_removed_with_del(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        class OptOutSpace(ParentSpace):
            def _get_migrations(self) -> dict[str, Migration]:
                migrations = super()._get_migrations()
                del migrations["unuse-old-tool"]
                return migrations

        with mock_ctx:
            OptOutSpace().lint()

        assert "unuse-old-tool" not in _err(capsys)


class TestSetupDevMigrations:
    @pytest.mark.parametrize("fast", [0, 1, 2])
    def test_setup_dev_applies_migrations_first_at_every_fast_level(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture, fast: int
    ) -> None:
        space = space_with({"unuse-old-tool": UnuseToolMigration(applies=True)})

        with mock_ctx, _setup_steps_stubbed(space):
            space.setup_dev(fast=fast)

        err = _err(capsys)
        description = err.index("Remove old-tool from mise.toml")
        applied = err.index("mise unuse old-tool")
        assert description < applied < err.index("Setting up project")
        if fast < 1:
            assert applied < err.index("Setting up platform tools")
        if fast < 2:
            assert applied < err.index("Setting up tools")

    def test_setup_dev_skips_migrations_that_no_longer_apply(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        space = space_with({"unuse-old-tool": UnuseToolMigration(applies=False)})

        with mock_ctx, _setup_steps_stubbed(space):
            space.setup_dev(fast=2)

        err = _err(capsys)
        assert "mise unuse old-tool" not in err
        assert "Remove old-tool from mise.toml" not in err

    def test_setup_dev_previews_file_migration_under_dry_run(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture, tmp_path: Path
    ) -> None:
        old_cfg = tmp_path / "old.cfg"
        old_cfg.write_text("")
        space = space_with({"delete-old-cfg": DeleteFileMigration(old_cfg)})

        with mock_ctx, _setup_steps_stubbed(space):
            space.setup_dev(fast=2)

        assert "Delete old.cfg" in _err(capsys)
        assert old_cfg.exists()

    def test_setup_dev_applies_file_migration_without_dry_run(
        self, mock_ctx: Context, tmp_path: Path
    ) -> None:
        old_cfg = tmp_path / "old.cfg"
        old_cfg.write_text("")
        space = space_with({"delete-old-cfg": DeleteFileMigration(old_cfg)})
        mock_ctx.dry_run = False

        with mock_ctx, _setup_steps_stubbed(space):
            space.setup_dev(fast=2)

        assert not old_cfg.exists()

    def test_failing_apply_exits_2_and_rerun_picks_up_the_rest(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture, tmp_path: Path
    ) -> None:
        old_cfg = tmp_path / "old.cfg"
        old_cfg.write_text("")
        mock_ctx.dry_run = False
        failing = space_with(
            {
                "delete-old-cfg": DeleteFileMigration(old_cfg),
                "fail": FailingMigration(),
                "unuse-old-tool": UnuseToolMigration(applies=True),
            }
        )

        with mock_ctx, _setup_steps_stubbed(failing), pytest.raises(typer.Exit) as exc_info:
            failing.setup_dev(fast=2)

        assert exc_info.value.exit_code == 2
        err = _err(capsys)
        assert "Migration fail failed: boom" in err
        assert "mise unuse old-tool" not in err
        assert not old_cfg.exists()

        rerun = space_with({"delete-old-cfg": DeleteFileMigration(old_cfg)})
        mock_ctx.dry_run = True
        with mock_ctx, _setup_steps_stubbed(rerun):
            rerun.setup_dev(fast=2)
        assert "Delete old.cfg" not in _err(capsys)

    def test_setup_dev_applies_parent_migrations_before_child(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        class ChildMigration(UnuseToolMigration):
            description = "Child step"

        class ChildSpace(ParentSpace):
            def _get_migrations(self) -> dict[str, Migration]:
                return {**super()._get_migrations(), "child-step": ChildMigration(applies=True)}

        space = ChildSpace()
        with mock_ctx, _setup_steps_stubbed(space):
            space.setup_dev(fast=2)

        err = _err(capsys)
        assert err.index("Remove old-tool from mise.toml") < err.index("Child step")


class TestUpdateMigrations:
    @pytest.mark.parametrize("managed", [True, False])
    def test_update_ends_with_post_update_in_a_fresh_process_keeping_bakefile_options(
        self,
        mock_ctx: Context,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        managed: bool,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        mock_ctx.obj.bakebook_name = "bakebook2"
        mock_ctx.obj.file_name = "tasks.py"
        mock_ctx.obj.chdir = Path("sub dir")
        mock_ctx.obj.use_global = True
        space = space_with({"unuse-old-tool": UnuseToolMigration(applies=True)})
        space.bake_manage_content = managed

        with mock_ctx:
            space.update(fast=2)

        err = _err(capsys)
        post_update = (
            "bake --chdir 'sub dir' --global --file-name tasks.py --book-name bakebook2 post-update"
        )
        assert err.rstrip().endswith(post_update)
        assert err.index("pre-commit autoupdate") < err.index(post_update)
        # the running process holds the outgoing version's Migrations
        assert "mise unuse old-tool" not in err
        assert "mc sync" not in err

    def test_post_update_applies_migrations_then_syncs_managed_content(
        self,
        mock_ctx: Context,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        space = space_with({"unuse-old-tool": UnuseToolMigration(applies=True)})
        space.bake_manage_content = True

        with mock_ctx:
            space.post_update()

        err = _err(capsys)
        assert err.index("Remove old-tool from mise.toml") < err.index("mise unuse old-tool")
        assert err.index("mise unuse old-tool") < err.index("would write oxfmt.config.ts")
        assert list(tmp_path.iterdir()) == []

    def test_post_update_skips_sync_when_managed_content_is_off(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        space = space_with({"unuse-old-tool": UnuseToolMigration(applies=True)})

        with mock_ctx:
            space.post_update()

        err = _err(capsys)
        assert "mise unuse old-tool" in err
        assert "Syncing managed content" not in err

    def test_post_update_failing_apply_exits_2(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        space = space_with({"fail": FailingMigration()})
        space.bake_manage_content = True

        with mock_ctx, pytest.raises(typer.Exit) as exc_info:
            space.post_update()

        assert exc_info.value.exit_code == 2
        err = _err(capsys)
        assert "Migration fail failed: boom" in err
        assert "Syncing managed content" not in err

    def test_post_update_is_hidden_from_help(self) -> None:
        result = CliRunner().invoke(BaseSpace()._app, ["--help"])

        assert result.exit_code == 0
        assert "update" in result.output
        assert "post-update" not in result.output


class DeadOptOutSpace(BaseSpace):
    def _get_migrations(self) -> dict[str, Migration]:
        migrations = super()._get_migrations()
        del migrations["removed-upstream"]
        return migrations


class TestDeadOptOut:
    @pytest.mark.parametrize(
        "run", [lambda s: s.lint(), lambda s: s.setup_dev(fast=2), lambda s: s.post_update()]
    )
    def test_del_of_missing_migration_exits_2_naming_the_key(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture, run
    ) -> None:
        space = DeadOptOutSpace()

        with mock_ctx, _setup_steps_stubbed(space), pytest.raises(typer.Exit) as exc_info:
            run(space)

        assert exc_info.value.exit_code == 2
        assert exc_info.value.__cause__ is None
        err = _err(capsys)
        assert "removed-upstream" in err
        assert "no longer exists upstream" in err
        assert "delete that line" in err
