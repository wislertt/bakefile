import subprocess
from email.message import Message
from http.client import IncompleteRead
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pytest

from bakelib.managed_content import ManagedContentError
from bakelib.space.utils.gitignore import GITHUB, Section, read_section, render_section

SHA_1 = "1" * 40


class TestGitignoreSection:
    def test_lines_the_engine_would_split_are_dropped_and_trailing_space_stripped(self) -> None:
        section = render_section(SHA_1, {"Global/macOS": "Icon[\r]\n.DS_Store  \r\n"})

        assert "### Global/macOS ###\n.DS_Store\n\n# End of" in section
        assert read_section(section) == Section(
            sha=SHA_1, paths=("Global/macOS",), text=section, intact=True
        )

    def test_missing_template_names_the_url(self) -> None:
        url = "https://raw.githubusercontent.com/github/gitignore/abc/Cobol.gitignore"
        error = HTTPError(url, 404, "Not Found", Message(), None)
        with (
            patch("urllib.request.urlopen", side_effect=error),
            pytest.raises(ManagedContentError, match=rf"'Cobol' is not in .*{url} answered 404"),
        ):
            GITHUB.template("abc", "Cobol")

    def test_download_cut_short_names_the_template_and_url(self) -> None:
        url = "https://raw.githubusercontent.com/github/gitignore/abc/Python.gitignore"
        response = MagicMock()
        response.__enter__.return_value.read.side_effect = IncompleteRead(b"")
        with (
            patch("urllib.request.urlopen", return_value=response),
            pytest.raises(ManagedContentError, match=rf"could not fetch .*'Python' from {url}"),
        ):
            GITHUB.template("abc", "Python")

    def test_latest_commit_is_read_from_main_with_git_ls_remote(self) -> None:
        listed = subprocess.CompletedProcess([], 0, stdout=f"{SHA_1}\trefs/heads/main\n")
        with patch("subprocess.run", return_value=listed) as run:
            sha = GITHUB.latest_sha()

        assert sha == SHA_1
        assert run.call_args.args[0] == [
            "git",
            "ls-remote",
            "https://github.com/github/gitignore",
            "refs/heads/main",
        ]

    @pytest.mark.parametrize(
        "error",
        [
            FileNotFoundError("git"),
            subprocess.CalledProcessError(128, "git"),
            subprocess.TimeoutExpired("git", 60),
        ],
    )
    def test_failing_git_ls_remote_names_the_repository(self, error: Exception) -> None:
        with (
            patch("subprocess.run", side_effect=error),
            pytest.raises(
                ManagedContentError,
                match=r"could not read the latest commit of https://github\.com/github/gitignore",
            ),
        ):
            GITHUB.latest_sha()

    def test_git_ls_remote_output_without_a_commit_is_an_error(self) -> None:
        listed = subprocess.CompletedProcess([], 0, stdout="")
        with (
            patch("subprocess.run", return_value=listed),
            pytest.raises(ManagedContentError, match="gave no commit for main"),
        ):
            GITHUB.latest_sha()
