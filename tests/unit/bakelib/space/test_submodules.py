import pytest

from bake import Context
from bake.ui.logger import strip_ansi
from bakelib.space.submodules import SubmodulesUtils


class TestSyncSubmodulesInternal:
    def test_sync_submodules_frozen_runs_without_remote_flag(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        utils = SubmodulesUtils()
        with mock_ctx:
            utils._sync_submodules(frozen=True)
        captured = capsys.readouterr()
        err = strip_ansi(captured.err)
        assert "git submodule update --init --recursive" in err
        assert "--remote" not in err

    def test_sync_submodules_not_frozen_runs_with_remote_flag(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        utils = SubmodulesUtils()
        with mock_ctx:
            utils._sync_submodules(frozen=False)
        captured = capsys.readouterr()
        err = strip_ansi(captured.err)
        assert "git submodule update --init --recursive --remote" in err


class TestSyncSubmodulesCommand:
    def test_sync_submodules_command_default_runs_with_remote(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        utils = SubmodulesUtils()
        with mock_ctx:
            utils.sync_submodules()
        captured = capsys.readouterr()
        err = strip_ansi(captured.err)
        assert "git submodule update --init --recursive --remote" in err

    def test_sync_submodules_command_with_frozen_flag(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        utils = SubmodulesUtils()
        with mock_ctx:
            utils.sync_submodules(frozen=True)
        captured = capsys.readouterr()
        err = strip_ansi(captured.err)
        assert "git submodule update --init --recursive" in err
        assert "--remote" not in err


class TestUpdate:
    def test_update_calls_sync_submodules_not_frozen(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        utils = SubmodulesUtils()
        with mock_ctx:
            utils.update()
        captured = capsys.readouterr()
        err = strip_ansi(captured.err)
        # Should contain submodule command with --remote
        assert "git submodule update --init --recursive --remote" in err


class TestSetupTools:
    def test__setup_tools_calls_sync_submodules_frozen(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        utils = SubmodulesUtils()
        with mock_ctx:
            utils._setup_tools()
        captured = capsys.readouterr()
        err = strip_ansi(captured.err)
        # Should contain submodule command without --remote
        assert "git submodule update --init --recursive" in err
        # Should NOT have --remote in submodule command
        lines = err.split("\n")
        submodule_lines = [line for line in lines if "submodule" in line]
        assert any("--remote" not in line for line in submodule_lines)


class TestAssertTools:
    def test_assert_tools_calls_sync_submodules_frozen(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        utils = SubmodulesUtils()
        with mock_ctx:
            utils._assert_tools()
        captured = capsys.readouterr()
        err = strip_ansi(captured.err)
        # Should contain submodule command without --remote
        assert "git submodule update --init --recursive" in err
