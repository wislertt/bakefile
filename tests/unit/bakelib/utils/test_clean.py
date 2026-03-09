from pathlib import Path

import pytest

from bake import Context
from bake.ui.logger import strip_ansi
from bakelib.utils.clean import (
    CleanUtils,
    _should_remove_path,
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


class TestCleanUtils:
    def test_clean_all_runs_git_clean(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        clean_utils = CleanUtils()
        with mock_ctx:
            clean_utils.clean_all()
        captured = capsys.readouterr()
        err = strip_ansi(captured.err)
        assert "git clean -fdX" in err

    def test_clean_with_default_excludes(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        clean_utils = CleanUtils()

        with mock_ctx:
            clean_utils.clean()

        captured = capsys.readouterr()
        err = strip_ansi(captured.err)
        assert "git clean -fdX -n" in err
        assert ".env" in err
        assert ".cache" in err

    def test_clean_without_default_excludes(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        clean_utils = CleanUtils()

        with mock_ctx:
            clean_utils.clean(default_excludes=False)

        captured = capsys.readouterr()
        err = strip_ansi(captured.err)
        assert "git clean -fdX -n" in err
        assert ".env" not in err
        assert ".cache" not in err

    def test_clean_with_custom_exclude_patterns(
        self, mock_ctx: Context, capsys: pytest.CaptureFixture
    ) -> None:
        clean_utils = CleanUtils()
        with mock_ctx:
            clean_utils.clean(exclude_patterns=["*.log", "*.tmp"])

        captured = capsys.readouterr()
        err = strip_ansi(captured.err)
        assert "git clean -fdX -n" in err
        assert "*.log" in err
        assert "*.tmp" in err
        assert ".env" in err  # default excludes still applied
        assert ".cache" in err
