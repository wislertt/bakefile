from pathlib import Path
from unittest.mock import patch

import pytest

from bake import Context
from bakelib.space.utils import (
    _should_remove_path,
    get_platform,
    remove_git_clean_candidates,
)


class TestShouldRemovePath:
    def test_dry_run_does_not_remove(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        _should_remove_path(test_file, dry_run=True)

        captured = capsys.readouterr()
        assert "Would remove" in captured.out
        assert test_file.exists()

    def test_dry_run_with_directory(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        _should_remove_path(test_dir, dry_run=True)

        captured = capsys.readouterr()
        assert "Would remove" in captured.out
        assert test_dir.exists()

    def test_non_dry_run_removes_file(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        _should_remove_path(test_file, dry_run=False)

        captured = capsys.readouterr()
        assert "Removing" in captured.out
        assert not test_file.exists()

    def test_non_dry_run_removes_directory(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("content")

        _should_remove_path(test_dir, dry_run=False)

        captured = capsys.readouterr()
        assert "Removing" in captured.out
        assert not test_dir.exists()


class TestRemoveGitCleanCandidates:
    def test_skips_lines_not_starting_with_would_remove(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        import os

        os.chdir(tmp_path)
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        output = "random line\nanother random line"
        remove_git_clean_candidates(output, set(), dry_run=True)

        captured = capsys.readouterr()
        assert "Skipping" not in captured.out
        assert "Would skip" not in captured.out
        assert "Would remove" not in captured.out
        assert test_file.exists()

    def test_skips_git_repository(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        import os

        os.chdir(tmp_path)
        git_dir = tmp_path / "submodule"
        git_dir.mkdir()
        (git_dir / ".git").mkdir()

        rel_path = str(git_dir.relative_to(tmp_path))
        output = f"Would remove {rel_path}"

        remove_git_clean_candidates(output, set(), dry_run=True)

        captured = capsys.readouterr()
        assert "git repository" in captured.out
        assert git_dir.exists()

    def test_skips_excluded_patterns(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        import os

        os.chdir(tmp_path)
        test_file = tmp_path / "test.log"
        test_file.write_text("content")

        rel_path = str(test_file.relative_to(tmp_path))
        output = f"Would remove {rel_path}"

        remove_git_clean_candidates(output, {"*.log"}, dry_run=True)

        captured = capsys.readouterr()
        assert "Skipping" in captured.out or "Would skip" in captured.out
        assert test_file.exists()

    def test_removes_matching_files_dry_run(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        import os

        os.chdir(tmp_path)
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        rel_path = str(test_file.relative_to(tmp_path))
        output = f"Would remove {rel_path}"

        remove_git_clean_candidates(output, set(), dry_run=True)

        captured = capsys.readouterr()
        assert "Would remove" in captured.out
        assert test_file.exists()

    def test_removes_matching_files_non_dry_run(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        import os

        os.chdir(tmp_path)
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        rel_path = str(test_file.relative_to(tmp_path))
        output = f"Would remove {rel_path}"

        remove_git_clean_candidates(output, set(), dry_run=False)

        captured = capsys.readouterr()
        assert "Removing" in captured.out
        assert not test_file.exists()

    def test_removes_matching_directories_non_dry_run(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        import os

        os.chdir(tmp_path)
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("content")

        rel_path = str(test_dir.relative_to(tmp_path))
        output = f"Would remove {rel_path}"

        remove_git_clean_candidates(output, set(), dry_run=False)

        captured = capsys.readouterr()
        assert "Removing" in captured.out
        assert not test_dir.exists()

    def test_handles_multiple_lines(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        import os

        os.chdir(tmp_path)
        file1 = tmp_path / "test.txt"
        file1.write_text("content")
        file2 = tmp_path / "test.log"
        file2.write_text("content")

        rel1 = str(file1.relative_to(tmp_path))
        rel2 = str(file2.relative_to(tmp_path))
        output = f"Would remove {rel1}\nWould remove {rel2}\nrandom line"

        remove_git_clean_candidates(output, {"*.log"}, dry_run=True)

        captured = capsys.readouterr()
        assert "Would remove" in captured.out
        assert file1.exists()
        assert file2.exists()

    def test_removes_file_with_missing_ok(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        import os

        os.chdir(tmp_path)
        test_file = tmp_path / "test.txt"

        rel_path = str(test_file.relative_to(tmp_path))
        output = f"Would remove {rel_path}"

        remove_git_clean_candidates(output, set(), dry_run=False)

        captured = capsys.readouterr()
        assert "Removing" in captured.out
        assert not test_file.exists()


class TestSetupFunctions:
    def test_setup_brew_runs_brew_commands(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        from bakelib.space.utils import setup_brew

        setup_brew(mock_ctx)
        captured = capsys.readouterr()
        assert "brew update" in captured.err
        assert "brew upgrade" in captured.err
        assert "brew cleanup" in captured.err
        assert "brew list" in captured.err
        assert "brew leaves" in captured.err

    def test_setup_bun_runs_brew_install_bun(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        from bakelib.space.utils import setup_bun

        setup_bun(mock_ctx)
        captured = capsys.readouterr()
        assert "brew install oven-sh/bun/bun" in captured.err


class TestGetPlatform:
    @pytest.mark.parametrize(
        "sys_platform,expected",
        [
            ("linux", "linux"),
            ("win32", "windows"),
            ("unknown", "other"),
        ],
    )
    @patch("bakelib.space.utils.sys.platform")
    def test_returns_correct_platform(
        self, _mock_platform: str, sys_platform: str, expected: str
    ) -> None:
        with patch("bakelib.space.utils.sys.platform", sys_platform):
            result = get_platform()
            assert result == expected
